import asyncio
import os
import json
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr
import sys

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

async def heal_playwright_script(failing_script_path: str, error_json_path: str) -> str:
    """
    Analyzes a failing Playwright script and its error report, then heals it using the Playwright MCP server.
    """
    # Load environment variables
    load_dotenv()

    # Read the content of the failing script and the error JSON
    try:
        with open(failing_script_path, "r", encoding="utf-8") as f:
            failing_script = f.read()
    except FileNotFoundError:
        print(f"Error: Failing script not found at {failing_script_path}")
        return ""
    except Exception as e:
        print(f"Error reading failing script: {e}")
        return ""

    try:
        with open(error_json_path, "r", encoding="utf-8") as f:
            error_details = json.load(f)
    except FileNotFoundError:
        print(f"Error: error.json not found at {error_json_path}")
        return ""
    except Exception as e:
        print(f"Error reading error.json: {e}")
        return ""

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
    except FileNotFoundError:
        print("Error: playwright_mcp.json not found. Please ensure the MCP server config is present.")
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
        print("Azure AI Initialized Successfully.")
    except Exception as e:
        print(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt for self-healing a Playwright script
    system_prompt = """
You are an expert AI test engineer integrated with a Playwright MCP server, capable of executing browser automation and DOM inspection tasks in real time.

Your task is to heal a failing Playwright test script. You are given:
1.  A failing Playwright test script.
2.  An `error.json` file detailing the failure (e.g., selector timeout).
3.  Live access to the application's DOM via the Playwright MCP server.

Your process must be:
1.  **Analyze**: Examine the failing script and the `error.json` to pinpoint the root cause.
2.  **Inspect & Identify**: Use the MCP server to inspect the live DOM. Identify flaky or broken selectors and determine their correct, resilient replacements.
3.  **Heal**: Modify *only the broken parts* of the script to fix the failure. Preserve all other working logic. Use robust selectors like `data-testid`, stable class names, or `getByRole`.
4.  **Output**: Provide the self-healed Playwright script and a summary.

**Output Format:**

### 🧩 Healing Summary
- **Failure Cause:** <Briefly explain why the original script failed, citing the error.json>
- **Fix Applied:** <Describe the exact change made (e.g., 'Replaced selector "old-selector" with `getByRole('button', { name: 'Submit' })`') and why.>
- **Suggested Fix:** <Recommend a long-term fix if applicable (e.g., 'Advise developers to add a `data-testid="submit-button"` for better stability.').>

### ✅ Healed Test Script
```typescript
<The complete, fixed Playwright script goes here>
"""

# Combine the system prompt with the specific failing data
    prompt = f"""
    {system_prompt}

    Here is the failing test data:

    Failing Playwright Script ({os.path.basename(failing_script_path)}):

    TypeScript

    {failing_script}
    Error Details ({os.path.basename(error_json_path)}):

    JSON

    {json.dumps(error_details, indent=2)}
    Please begin the healing process.
    """

    # Run agent with retry logic for content filter errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt, max_steps=30)
            # The entire response including the summary and code is the result
            if "### ✅ Healed Test Script" in result:
                return result
            else:
                print("The agent's response did not contain a healed test script.")
                return ""
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                print(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                await asyncio.sleep(2)  # Wait before retrying
                continue
            print(f"An unexpected error occurred while running the agent: {e}")
            return ""

    print("Failed to get a valid response from the agent after multiple retries.")
    return ""
async def main():
        """Main function to execute the script healing process."""
        if len(sys.argv) != 3:
        print("Usage: python heal_script.py <path_to_failing_script.spec.ts> <path_to_error.json>")
        sys.exit(1)

        failing_script_path = sys.argv[1]
        error_json_path = sys.argv[2]

        print(f"\nAttempting to heal script:\n- Test: {failing_script_path}\n- Error: {error_json_path}\n")

        healed_output = await heal_playwright_script(failing_script_path, error_json_path)

        if healed_output:
            # Generate a unique filename for the healed script in the 'healed_tests' directory
            base_name = os.path.splitext(os.path.basename(failing_script_path))[0]
            healed_filename = base_name.replace('.spec', '_healed.spec')
            test_file_path = get_unique_filename(healed_filename, ".ts", HEALED_TESTS_DIR)
            
            try:
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write(healed_output)
                print(f"\nHealing successful!")
                print(f"Healed test script and summary saved to: {test_file_path}")
            except IOError as e:
                print(f"Error saving the healed test script: {e}")
        else:
            print("\nFailed to heal the test script.")
            
if name == "main":
    asyncio.run(main())