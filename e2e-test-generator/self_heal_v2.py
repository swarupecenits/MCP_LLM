import asyncio
import os
import json
import logging
import argparse
import chardet
import re
import sys
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Directory to save healed test scripts
HEALED_TESTS_DIR = "healed_tests"

# Ensure the directory for healed tests exists
if not os.path.exists(HEALED_TESTS_DIR):
    os.makedirs(HEALED_TESTS_DIR)

def get_unique_filename(base_name: str, extension: str, directory: str) -> str:
    """Generate a unique filename by appending an incrementing number if the base name already exists."""
    counter = 1
    file_path = os.path.join(directory, f"{base_name}{extension}")
    while os.path.exists(file_path):
        filename = f"{base_name}_{counter}{extension}"
        file_path = os.path.join(directory, filename)
        counter += 1
    return file_path

async def heal_playwright_script(failing_script_path: str, error_json_path: str) -> tuple[str, str]:
    """
    Analyzes a failing Playwright script and its error report, then heals it using the Playwright MCP server.
    Returns a tuple of (healing_summary, healed_script).
    """
    # Load environment variables
    load_dotenv()
    if not os.getenv('AZURE_OPENAI_ENDPOINT') or not os.getenv('AZURE_OPENAI_API_KEY'):
        logging.error("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY environment variables.")
        return "", ""

    # Read the content of the failing script
    try:
        with open(failing_script_path, "r", encoding="utf-8") as f:
            failing_script = f.read()
        logging.info(f"Loaded failing script from {failing_script_path}")
    except FileNotFoundError:
        logging.error(f"Failing script not found at {failing_script_path}")
        return "", ""
    except UnicodeDecodeError as e:
        logging.error(f"Failed to decode {failing_script_path} with UTF-8: {e}")
        return "", ""
    except Exception as e:
        logging.error(f"Error reading failing script: {e}")
        return "", ""

    # Detect encoding of error.json using chardet
    try:
        with open(error_json_path, "rb") as f:
            raw_data = f.read()
        if not raw_data:
            logging.error(f"{error_json_path} is empty")
            return "", ""
        result = chardet.detect(raw_data)
        detected_encoding = result['encoding']
        confidence = result['confidence']
        logging.info(f"Detected encoding for {error_json_path}: {detected_encoding} (confidence: {confidence:.2f})")
        if detected_encoding is None:
            logging.warning(f"chardet could not detect encoding for {error_json_path}")
            detected_encoding = 'utf-8'  # Fallback to UTF-8
        if confidence < 0.7:
            logging.warning(f"Low confidence ({confidence:.2f}) in detected encoding {detected_encoding} for {error_json_path}")
    except FileNotFoundError:
        logging.error(f"Result JSON not found at {error_json_path}")
        return "", ""
    except Exception as e:
        logging.error(f"Error reading {error_json_path} in binary mode: {e}")
        return "", ""

    # Read error.json with detected encoding or fallbacks
    error_details = None
    encodings_to_try = [detected_encoding] if detected_encoding else ['utf-8']
    encodings_to_try.extend(['utf-8-sig', 'latin1'])  # Additional fallbacks
    for encoding in encodings_to_try:
        try:
            decoded_data = raw_data.decode(encoding)
            error_details = json.loads(decoded_data)
            logging.info(f"Successfully parsed {error_json_path} as JSON using {encoding} encoding")
            break
        except UnicodeDecodeError as e:
            logging.warning(f"Failed to decode {error_json_path} with {encoding}: {e}")
            continue
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {error_json_path} with {encoding}: {e}")
            snippet = decoded_data[:100].replace('\n', '\\n') if 'decoded_data' in locals() else "N/A"
            hex_bytes = raw_data[:16].hex() if raw_data else "N/A"
            logging.error(f"File snippet (first 100 chars): {snippet}")
            logging.error(f"First 16 bytes (hex): {hex_bytes}")
            logging.error(f"Please verify {error_json_path} is valid JSON. Try opening in a text editor or running 'head {error_json_path}'.")
            continue
        except Exception as e:
            logging.error(f"Error parsing {error_json_path} with {encoding}: {e}")
            continue

    if error_details is None:
        logging.error(f"Failed to parse {error_json_path} as JSON with any encoding (tried: {', '.join(encodings_to_try)})")
        return "", ""

    # Extract specific error details
    error_context = {
        "type": "Unknown",
        "message": "",
        "selector": "",
        "line_number": None
    }
    has_errors = False
    if error_details.get('errors', []):
        error_context["type"] = "GlobalError"
        error_context["message"] = error_details['errors'][0].get('message', '')
        error_context["line_number"] = error_details['errors'][0].get('location', {}).get('line')
        logging.info(f"Global errors found in {error_json_path}: {len(error_details['errors'])} error(s)")
        has_errors = True
    elif error_details.get('suites', []):
        for suite in error_details['suites']:
            for spec in suite.get('specs', []):
                for test in spec.get('tests', []):
                    for result in test.get('results', []):
                        if result.get('status') != 'passed':
                            error_context["type"] = result.get('status', 'Failed')
                            error_context["message"] = result.get('error', {}).get('message', '')
                            # Extract selector from error message if possible
                            selector_match = re.search(r'locator\(["\'](.+?)["\']\)', error_context["message"])
                            if selector_match:
                                error_context["selector"] = selector_match.group(1)
                            logging.info(f"Test failure found in {error_json_path}: {result.get('status')} for test '{spec.get('title')}'")
                            has_errors = True
                            break
                    if has_errors:
                        break
                if has_errors:
                    break
    elif error_details.get('stats', {}).get('unexpected', 0) > 0:
        error_context["type"] = "UnexpectedFailure"
        error_context["message"] = f"{error_details['stats']['unexpected']} unexpected test failures"
        logging.info(f"Unexpected test failures found in {error_json_path}: {error_details['stats']['unexpected']} failure(s)")
        has_errors = True

    if not has_errors:
        logging.info("No error encountered - Script not required to HEAL")
        sys.exit(0)

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("scripts/e2e-test-generator/playwright_mcp.json")
        logging.info("Connected to MCP server successfully")
    except FileNotFoundError:
        logging.error("playwright_mcp.json not found. Please ensure the MCP server config is present.")
        return "", ""
    except Exception as e:
        logging.error(f"Error loading MCP client configuration: {e}")
        return "", ""

    # Initialize LLM
    try:
        llm = AzureChatOpenAI(
            model="gpt-4o",
            azure_deployment="gpt-4o",
            api_version="2023-07-01-preview",
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            api_key=SecretStr(os.getenv('AZURE_OPENAI_API_KEY', '')),
            temperature=0.1,
        )
        logging.info("Azure AI Initialized Successfully")
    except Exception as e:
        logging.error(f"Error initializing AzureChatOpenAI: {e}")
        return "", ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # Enhanced system prompt for self-healing
    system_prompt = """
You are an expert AI test engineer integrated with a Playwright MCP server, capable of executing browser automation and DOM inspection tasks in real time for the Azure AI Studio workspace-portal application at https://ai.azure.com?auth=local.

Your task is to heal a failing Playwright test script by addressing errors such as missing selectors, timeouts, or other failures. You are given:
1. A failing Playwright test script.
2. An `error.json` file detailing the failure (e.g., selector timeout, element not found).
3. Live access to the application's DOM via the Playwright MCP server.
4. Specific error context (error type, message, selector, line number).

Your process must be:
1. **Analyze**: Examine the failing script, `error.json`, and error context to pinpoint the root cause (e.g., timeout due to low timeout value, missing selector due to DOM change).
2. **Inspect & Identify**: Use the MCP server to inspect the live DOM. Identify flaky or broken selectors and determine their correct, resilient replacements. Prioritize:
   - `getByTestId` for elements with `data-testid` attributes.
   - `getByRole` for semantic elements (e.g., `button`, `link`) with accessible names.
   - `getByText` for visible text content.
   - `getByLabel` for form elements with labels.
   - CSS or XPath selectors only as a last resort, and justify their use.
3. **Heal**: Modify *only the broken parts* of the script to fix the failure. Preserve all other working logic. Apply these strategies:
   - For timeout errors, increase the timeout (e.g., to 30000ms) or add `waitFor` conditions.
   - For missing selectors, replace with robust locators based on DOM inspection.
   - For flaky tests, add retry logic (e.g., `page.waitForTimeout(1000)` or polling).
   - Ensure strict mode compliance (unique element matches).
4. **Validate**: Ensure the healed script uses robust locators. Warn if CSS/XPath is used excessively.
5. **Output**: Provide a healing summary and the self-healed Playwright script. If the UI has changed significantly, suggest visual regression testing (note: not implemented).

Output Format:

### 🧩 Healing Summary
- Failure Cause: <Briefly explain why the original script failed, citing the error.json and error context>
- Fix Applied: <Describe the exact change made (e.g., 'Increased timeout from 1ms to 30000ms', 'Replaced selector "old-selector" with `getByRole('button', { name: 'Submit' })`') and why>
- Suggested Fix: <Recommend a long-term fix (e.g., 'Add `data-testid="submit-button"` to the element', 'Implement visual regression testing for UI stability')>

```typescript
<The complete, fixed Playwright script goes here>
```
"""
    # Combine the system prompt with the specific failing data
    prompt = f"""
{system_prompt}

Here is the failing test data:

Failing Playwright Script ({os.path.basename(failing_script_path)}):

```typescript
{failing_script}
```

Error Details ({os.path.basename(error_json_path)}):

```json
{json.dumps(error_details, indent=2)}
```

Error Context:
- Type: {error_context['type']}
- Message: {error_context['message']}
- Selector: {error_context['selector']}
- Line Number: {error_context['line_number'] or 'N/A'}

Please begin the healing process.
"""

    # Run agent with retry logic for content filter errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt, max_steps=30)
            # Extract the healing summary and healed script
            match = re.search(r'### 🧩 Healing Summary\n([\s\S]*?)\n```typescript\n([\s\S]*?)\n```', result)
            if match:
                healing_summary = match.group(1).strip()
                healed_script = match.group(2).strip()
                # Validate healed script for robust locators
                css_xpath_count = len(re.findall(r'locator\(["\'].*?(?:\.|//).*?["\']\)', healed_script))
                if css_xpath_count > 1:
                    logging.warning(f"Healed script contains {css_xpath_count} CSS/XPath selectors. Consider using getByTestId, getByRole, or getByText for better stability.")
                logging.info("Healed script and summary extracted successfully")
                return healing_summary, healed_script
            else:
                logging.error("The agent's response did not contain a healing summary and healed test script.")
                return "", ""
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                logging.warning(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                await asyncio.sleep(2)  # Wait before retrying
                continue
            logging.error(f"An unexpected error occurred while running the agent: {e}")
            return "", ""

    logging.error("Failed to get a valid response from the agent after multiple retries.")
    return "", ""

async def main():
    """Main function to execute the script healing process."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Heal a failing Playwright test script")
    parser.add_argument('--script', required=True, help="Path to the failing Playwright test script")
    parser.add_argument('--error', required=True, help="Path to the error.json file")
    args = parser.parse_args()

    logging.info(f"\nAttempting to heal script:\n- Test: {args.script}\n- Result: {args.error}\n")

    healing_summary, healed_script = await heal_playwright_script(args.script, args.error)

    if healed_script:
        # Generate a unique filename for the healed script in the 'healed_tests' directory
        base_name = os.path.splitext(os.path.basename(args.script))[0]
        healed_filename = f"{base_name}_healed_v1"
        test_file_path = get_unique_filename(healed_filename, ".spec.ts", HEALED_TESTS_DIR)

        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(healed_script)
            logging.info(f"\nHealing successful!\nHealed test script saved to: {test_file_path}")
            logging.info(f"\n### 🧩 Healing Summary\n{healing_summary}")
        except IOError as e:
            logging.error(f"Error saving the healed test script: {e}")
    else:
        logging.error("\nFailed to heal the test script.")

if __name__ == "__main__":
    asyncio.run(main())