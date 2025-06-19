import asyncio
import os
import json
import re
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr
import sys
import chardet

async def heal_failing_test(test_file_path: str, error_file_path: str) -> str:
    """Heal a failing Playwright test using MCP server DOM inspection."""
    # Load environment variables
    load_dotenv()

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
    except FileNotFoundError:
        print("Error: playwright_mcp.json not found")
        return ""
    except Exception as e:
        print(f"Error loading MCP client configuration: {e}")
        return ""

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
        print(f"Azure AI Initialized Successfully")
    except Exception as e:
        print(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Read the failing test script with automatic encoding detection
    try:
        # First, detect the file encoding
        with open(test_file_path, 'rb') as f:
            raw_data = f.read()
            detected_encoding = chardet.detect(raw_data)
            encoding = detected_encoding['encoding'] or 'utf-8'
            print(f"Detected encoding for test file: {encoding}")
        
        # Now read with the detected encoding
        with open(test_file_path, 'r', encoding=encoding) as f:
            failing_test_script = f.read()
    except FileNotFoundError:
        print(f"Error: Test file {test_file_path} not found")
        return ""
    except Exception as e:
        print(f"Error reading test file: {e}")
        return ""

    # Read the error details with automatic encoding detection
    try:
        # First, detect the file encoding
        with open(error_file_path, 'rb') as f:
            raw_data = f.read()
            detected_encoding = chardet.detect(raw_data)
            encoding = detected_encoding['encoding'] or 'utf-8'
            print(f"Detected encoding for error file: {encoding}")
        
        # Now read with the detected encoding
        with open(error_file_path, 'r', encoding=encoding) as f:
            error_details = json.load(f)
    except FileNotFoundError:
        print(f"Error: Error file {error_file_path} not found")
        return ""
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from error file: {e}")
        return ""
    except Exception as e:
        print(f"Error reading error file: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt for test healing
    system_prompt = """
You are an expert AI test engineer integrated with a Playwright MCP server, capable of executing browser automation and DOM inspection tasks in real time.

You are given:
- A failing Playwright test script.
- An `error.json` file that includes details about the failure (e.g., selector not found, timeout, etc.).
- Access to the current DOM of the application via the MCP server.

Your task is to:
1. Analyze the failing test script and `error.json` to determine the root cause.
2. Identify flaky or broken selectors and determine their correct replacements by inspecting the live DOM via the Playwright MCP server.
3. Heal the failing Playwright script by modifying only the broken parts — preserve working logic.
4. Output the **self-healed Playwright test script**.
5. Include a summary section at the top that:
   - Describes the cause of failure.
   - Describes the fix applied (e.g., selector replaced, wait added).
   - Mentions the suggested long-term fix if applicable (e.g., use a stable attribute or test ID).

You must:
- Use selectors that are resilient and descriptive (`data-testid`, stable classes, etc.).
- Log any ambiguity or uncertainty clearly in the summary.
- Test the new script on the page (via DOM query) before finalizing it.
- Output only valid Playwright script using `@playwright/test`.

Format:

### 🧩 Healing Summary
- **Failure Cause:** <briefly explain why the original script failed>
- **Fix Applied:** <what was changed and why>
- **Suggested Fix:** <what devs can change to make the test more stable>

### ✅ Healed Test Script
```ts
<fixed playwright script here>
```

It must follow this format for any test script.
"""

    # Combine system prompt with test script and error details
    prompt = f"""{system_prompt}

## Failing Test Script:
```typescript
{failing_test_script}
```

## Error Details:
```json
{json.dumps(error_details, indent=2)}
```

Please analyze the failure, inspect the live DOM using the MCP server, and provide a healed test script following the specified format.
"""

    # Run agent with retry logic for content filter errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt, max_steps=30)
            return result
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                print(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            print(f"Error running agent: {e}")
            return ""

def save_healed_test(healed_content: str, original_test_path: str) -> str:
    """Save the healed test script to a new file."""
    # Extract the directory and filename
    test_dir = os.path.dirname(original_test_path)
    original_filename = os.path.basename(original_test_path)
    
    # Create healed filename
    name_without_ext = os.path.splitext(original_filename)[0]
    healed_filename = f"{name_without_ext}_healed.spec.ts"
    healed_path = os.path.join(test_dir, healed_filename)
    
    # Extract only the TypeScript code block from the healed content
    code_match = re.search(r'### ✅ Healed Test Script\s*```ts\n([\s\S]*?)\n```', healed_content)
    if code_match:
        test_script_content = code_match.group(1)
        try:
            with open(healed_path, 'w', encoding='utf-8') as f:
                f.write(test_script_content)
            print(f"Healed test script saved to: {healed_path}")
            return healed_path
        except IOError as e:
            print(f"Error saving healed test script: {e}")
            return ""
    else:
        print("Could not extract healed test script from response")
        # Save the full response for debugging
        debug_path = os.path.join(test_dir, f"{name_without_ext}_healing_response.md")
        try:
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(healed_content)
            print(f"Full healing response saved to: {debug_path}")
        except IOError as e:
            print(f"Error saving debug response: {e}")
        return ""

async def main():
    """Main function to handle command line arguments and orchestrate test healing."""
    if len(sys.argv) < 3:
        print("Usage: python test_healer.py <test_file_path> <error_file_path>")
        print("Example: python test_healer.py tests/login.spec.ts tests/error.json")
        sys.exit(1)
    
    test_file_path = sys.argv[1]
    error_file_path = sys.argv[2]
    
    # Validate input files exist
    if not os.path.exists(test_file_path):
        print(f"Error: Test file '{test_file_path}' does not exist")
        sys.exit(1)
    
    if not os.path.exists(error_file_path):
        print(f"Error: Error file '{error_file_path}' does not exist")
        sys.exit(1)
    
    print(f"\nHealing failing Playwright test:")
    print(f"Test file: {test_file_path}")
    print(f"Error file: {error_file_path}\n")
    
    # Heal the failing test
    healed_result = await heal_failing_test(test_file_path, error_file_path)
    
    if healed_result:
        print("=== HEALING ANALYSIS ===")
        print(healed_result)
        print("\n" + "="*50 + "\n")
        
        # Save the healed test script
        healed_file_path = save_healed_test(healed_result, test_file_path)
        if healed_file_path:
            print(f"Success! Healed test saved to: {healed_file_path}")
        else:
            print("Failed to save healed test script")
    else:
        print("Failed to heal the test script")

if __name__ == "__main__":
    asyncio.run(main())