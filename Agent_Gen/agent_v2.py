import asyncio
import os
import re
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr
import sys

# Directory to save test scripts
TESTS_DIR = "tests"
ARTIFACTS_DIR = "artifacts"

# Ensure directories exist
for directory in [TESTS_DIR, ARTIFACTS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_unique_filename(base_name: str, extension: str, directory: str) -> str:
    """Generate a unique filename by appending an incrementing number."""
    counter = 1
    while True:
        filename = f"{base_name}_{counter}{extension}"
        file_path = os.path.join(directory, filename)
        if not os.path.exists(file_path):
            return file_path
        counter += 1

async def generate_playwright_script(user_task: str) -> str:
    """Generate a Playwright TypeScript test script based on the user task using MCP server navigation."""
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
            api_key=SecretStr(os.getenv('AZURE_OPENAI_KEY', '')),
            temperature=0,
        )
    except Exception as e:
        print(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt for Playwright MCP server navigation and script generation
    system_prompt = """
You are a Playwright test automation expert. Use the Playwright MCP server to perform browser navigation according to the provided user instructions. After completing the navigation and actions, generate a Playwright test script in TypeScript that exactly replicates the actions taken. The script must follow Playwright's best practices, including:
- Use async/await syntax.
- Import { test, expect } from '@playwright/test'.
- Use robust locators (e.g., getByRole, getByText).
- Include appropriate timeouts (e.g., 10000ms for visibility checks).
- Handle dynamic page loads with waitUntil: 'networkidle' or waitForURL.
- Include error handling (e.g., consent popups, visibility checks before interactions).
- Provide the script in a ```typescript code block.
Record the actions performed during navigation and ensure the generated script accurately reflects them.
"""

    # Combine system prompt and user task
    prompt = f"{system_prompt}\n\nUser Instructions:\n{user_task}"

    # Run agent with retry logic for content filter errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt, max_steps=30)
            # Extract TypeScript code block
            code_match = re.search(r'```typescript\n([\s\S]*?)\n```', result)
            if code_match:
                return code_match.group(1)
            else:
                print("No TypeScript code block found in the agent's response")
                return ""
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                print(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            print(f"Error running agent: {e}")
            return ""

# Default user task
DEFAULT_USER_TASK = """
1. Navigate to https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47.
2. Search for Model Catalogue.
3. Search for Azure Speech.
4. See if the Azure AI Speech is visible or not
4. Close the browser.
"""

async def main():
    # Get user task from command-line argument or use default
    if len(sys.argv) > 1:
        user_task = sys.argv[1]
    else:
        user_task = DEFAULT_USER_TASK

    print(f"Generating Playwright script for task:\n{user_task}")

    # Generate the test script
    test_script = await generate_playwright_script(user_task)

    if test_script:
        # Save to tests directory
        test_file_path = get_unique_filename("generated_test_output", ".spec.ts", TESTS_DIR)
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_script)
            print(f"Test script saved to {test_file_path}")

            # Save log
            log_file = get_unique_filename("agent-logs", ".json", ARTIFACTS_DIR)
            with open(log_file, "w", encoding="utf-8") as f:
                import json
                json.dump({
                    "user_task": user_task,
                    "generated_script": test_script,
                    "status": "success"
                }, f, indent=2)
            print(f"Logs saved to {log_file}")
        except IOError as e:
            print(f"Error saving test script or log: {e}")
    else:
        print("Failed to generate test script")
        # Save log for failure
        log_file = get_unique_filename("agent-logs", ".json", ARTIFACTS_DIR)
        with open(log_file, "w", encoding="utf-8") as f:
            import json
            json.dump({
                "user_task": user_task,
                "generated_script": None,
                "status": "failed"
            }, f, indent=2)
        print(f"Logs saved to {log_file}")

if __name__ == "__main__":
    asyncio.run(main())