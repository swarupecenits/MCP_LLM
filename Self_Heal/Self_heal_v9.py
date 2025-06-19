import asyncio
import os
import json
import logging
import argparse
import chardet
import re
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
        if confidence < 0.7:
            logging.warning(f"Low confidence ({confidence:.2f}) in detected encoding {detected_encoding} for {error_json_path}")
    except FileNotFoundError:
        logging.error(f"Error JSON not found at {error_json_path}")
        return "", ""
    except Exception as e:
        logging.error(f"Error reading {error_json_path} in binary mode: {e}")
        return "", ""

    # Read error.json with detected encoding
    try:
        error_details = json.loads(raw_data.decode(detected_encoding))
        logging.info(f"Successfully parsed {error_json_path} as JSON")
    except UnicodeDecodeError as e:
        logging.error(f"Failed to decode {error_json_path} with {detected_encoding}: {e}")
        return "", ""
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in {error_json_path}: {e}")
        return "", ""
    except Exception as e:
        logging.error(f"Error parsing {error_json_path} as JSON: {e}")
        return "", ""

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
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
            temperature=0,
        )
        logging.info("Azure AI Initialized Successfully")
    except Exception as e:
        logging.error(f"Error initializing AzureChatOpenAI: {e}")
        return "", ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt for self-healing a Playwright script
    system_prompt = """
You are an expert AI test engineer integrated with a Playwright MCP server, capable of executing browser automation and DOM inspection tasks in real time for the Azure AI Studio workspace-portal application at https://ai.azure.com?auth=local.

Your task is to heal a failing Playwright test script. You are given:
1. A failing Playwright test script.
2. An `error.json` file detailing the failure (e.g., selector timeout).
3. Live access to the application's DOM via the Playwright MCP server.

Your process must be:
1. Analyze: Examine the failing script and the `error.json` to pinpoint the root cause.
2. Inspect & Identify: Use the MCP server to inspect the live DOM. Identify flaky or broken selectors and determine their correct, resilient replacements.
3. Heal: Modify *only the broken parts* of the script to fix the failure. Preserve all other working logic. Use robust selectors like `data-testid`, stable class names, or `getByRole`.
4. Output: Provide a healing summary and the self-healed Playwright script.

Output Format:

Healing Summary
- Failure Cause: <Briefly explain why the original script failed, citing the error.json>
- Fix Applied: <Describe the exact change made (e.g., 'Replaced selector "old-selector" with `getByRole('button', { name: 'Submit' })`') and why.>
- Suggested Fix: <Recommend a long-term fix if applicable (e.g., 'Advise developers to add a `data-testid="submit-button"` for better stability.').>

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

    logging.info(f"\nAttempting to heal script:\n- Test: {args.script}\n- Error: {args.error}\n")

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
            logging.info(f"\nHealing Summary\n{healing_summary}")
        except IOError as e:
            logging.error(f"Error saving the healed test script: {e}")
    else:
        logging.error("\nFailed to heal the test script.")

if __name__ == "__main__":
    asyncio.run(main())