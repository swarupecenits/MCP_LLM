import asyncio
import os
import re
import json
import logging
import argparse
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Directory to save healed test scripts
TESTS_DIR = "tests"

# Ensure tests directory exists
if not os.path.exists(TESTS_DIR):
    os.makedirs(TESTS_DIR)

def get_unique_filename(base_name: str, extension: str, directory: str) -> str:
    """Generate a unique filename by appending an incrementing number."""
    counter = 1
    while True:
        filename = f"{base_name}_{counter}{extension}"
        file_path = os.path.join(directory, filename)
        if not os.path.exists(file_path):
            return file_path
        counter += 1

async def heal_playwright_script(script_path: str, error_path: str) -> str:
    """Heal a failing Playwright test script using error details and live DOM inspection."""
    # Load environment variables
    load_dotenv()
    if not os.getenv('AZURE_OPENAI_ENDPOINT') or not os.getenv('AZURE_OPENAI_API_KEY'):
        logging.error("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY environment variables.")
        return ""

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
        logging.info("Connected to MCP server successfully")
    except FileNotFoundError:
        logging.error("playwright_mcp.json not found")
        return ""
    except Exception as e:
        logging.error(f"Error loading MCP client configuration: {e}")
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
        logging.info("Azure AI Initialized Successfully")
    except Exception as e:
        logging.error(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # Read the failing test script
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            failing_script = f.read()
        logging.info(f"Loaded failing test script from {script_path}")
    except FileNotFoundError:
        logging.error(f"Failing test script not found at {script_path}")
        return ""
    except Exception as e:
        logging.error(f"Error reading test script: {e}")
        return ""

    # Read the error.json file
    try:
        with open(error_path, "r", encoding="utf-8") as f:
            error_data = json.load(f)
        logging.info(f"Loaded error details from {error_path}")
    except FileNotFoundError:
        logging.error(f"Error file not found at {error_path}")
        return ""
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in error file: {e}")
        return ""
    except Exception as e:
        logging.error(f"Error reading error file: {e}")
        return ""

    # System prompt for healing Playwright test scripts
    system_prompt = """
You are an expert AI test engineer integrated with a Playwright MCP server, capable of executing browser automation and DOM inspection tasks in real time for the Azure AI Studio workspace-portal application at https://ai.azure.com?auth=local.

You are given:
- A failing Playwright test script.
- An error.json file that includes details about the failure (e.g., selector not found, timeout, etc.).
- Access to the current DOM of the application via the Playwright MCP server.

Your task is to:
1. Analyze the failing test script and error.json to determine the root cause of the failure.
2. Identify flaky or broken selectors and determine their correct replacements by inspecting the live DOM via the Playwright MCP server.
3. Heal the failing Playwright script by modifying only the broken parts — preserve working logic.
4. Test the new script on the page (via DOM query) before finalizing it.
5. Output the healed Playwright test script in a ```typescript code block, preceded by a healing summary in the following format:

### 🧩 Healing Summary
- **Failure Cause:** <briefly explain why the original script failed>
- **Fix Applied:** <what was changed and why>
- **Suggested Fix:** <what devs can change to make the test more stable>

You must:
- Use selectors that are resilient and descriptive (e.g., data-testid, stable classes).
- Log any ambiguity or uncertainty clearly in the summary.
- Ensure the script uses `@playwright/test` and follows Playwright best practices (e.g., async syntax, robust locators, timeouts, error handling).
- Only output valid Playwright TypeScript code.
"""

    # Combine system prompt, failing script, and error details
    prompt = f"{system_prompt}\n\nFailing Test Script:\n```typescript\n{failing_script}\n```\n\nError Details:\n```json\n{json.dumps(error_data, indent=2)}\n```"

    # Run agent with retry logic for content filter errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt, max_steps=30)
            # Extract the healed script and summary
            summary_match = re.search(r'### 🧩 Healing Summary\n([\s\S]*?)\n### ✅ Healed Test Script\n```typescript\n([\s\S]*?)\n```', result)
            if summary_match:
                logging.info("Healed script and summary extracted successfully")
                return summary_match.group(0)  # Return the full output with summary and script
            else:
                logging.error("No healed script or summary found in the agent's response")
                return ""
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                logging.warning(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            logging.error(f"Error running agent: {e}")
            return ""

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Heal a failing Playwright test script")
    parser.add_argument('--script', required=True, help="Path to the failing Playwright test script")
    parser.add_argument('--error', required=True, help="Path to the error.json file")
    args = parser.parse_args()

    # Log the input files
    logging.info(f"Processing failing script: {args.script}")
    logging.info(f"Using error details from: {args.error}")

    # Heal the test script
    healed_output = await heal_playwright_script(args.script, args.error)

    if healed_output:
        # Save to tests directory
        test_file_path = get_unique_filename("healed_test_output", ".spec.ts", TESTS_DIR)
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(healed_output)
            logging.info(f"Healed test script saved to {test_file_path}")
        except IOError as e:
            logging.error(f"Error saving healed test script: {e}")
    else:
        logging.error("Failed to heal test script")

if __name__ == "__main__":
    asyncio.run(main())
