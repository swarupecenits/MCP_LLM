import asyncio
import os
import re
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

# Directory to save test scripts
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

async def generate_playwright_script(user_task: str) -> str:
    """Generate a Playwright TypeScript test script based on the user task using MCP server navigation."""
    # Load environment variables
    load_dotenv()
    if not os.getenv('AZURE_OPENAI_ENDPOINT') or not os.getenv('AZURE_OPENAI_API_KEY'):
        logging.error("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY environment variables.")
        return ""

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
        logging.info("Connected to MCP server successfully")
    except Exception as e:
        logging.error(f"Error loading MCP client configuration: {e}")
        return ""

    # Initialize LLM
    try:
        llm = AzureChatOpenAI(
            model="gpt-4.1",
            azure_deployment="gpt-4.1",
            api_version="2024-12-01-preview",
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            api_key=SecretStr(os.getenv('AZURE_OPENAI_API_KEY', '')),
            temperature=0.1,
        )
    except Exception as e:
        logging.error(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt for Playwright MCP server navigation and script generation
    system_prompt = """
You are a Playwright test automation expert for the Azure AI Studio workspace-portal application at https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47. Use the Playwright MCP server to perform browser navigation according to the provided user instructions. After completing the navigation and actions, generate a Playwright test script in TypeScript that replicates the actions taken. The script must follow Playwright's best practices, including:
- Use async syntax for all operations.
- Import { test, expect } from '@playwright/test'.
- Use robust locators (e.g., getByRole, getByText).
- Include timeouts (e.g., 10000ms for visibility checks).
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
                logging.error("No TypeScript code block found in the agent's response")
                return ""
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                logging.warning(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            logging.error(f"Error running agent: {e}")
            return ""

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate Playwright test script from PR description")
    parser.add_argument('--task', required=True, help="PR description to generate test script")
    args = parser.parse_args()

    # Use the task directly from the command-line argument
    user_task = args.task.strip()
    logging.info(f"Using PR description:\n{user_task}")

    # Generate the test script
    test_script = await generate_playwright_script(user_task)

    if test_script:
        # Save to tests directory
        test_file_path = get_unique_filename("generated_test_output", ".spec.ts", TESTS_DIR)
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_script)
            logging.info(f"Test script saved to {test_file_path}")
        except IOError as e:
            logging.error(f"Error saving test script: {e}")
    else:
        logging.error("Failed to generate test script")

if __name__ == "__main__":
    asyncio.run(main())