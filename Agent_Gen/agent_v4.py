import asyncio
import os
import re
import logging
import sys
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
sys.stdout.reconfigure(encoding='utf-8')

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
    client = MCPClient.from_config_file("playwright_mcp.json")
    logging.info(f"Connected to MCP server successfully")


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
    except Exception as e:
        logging.error(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt for Playwright MCP server navigation and script generation
    system_prompt = """
You are a Playwright test automation expert. Use the Playwright MCP server to perform browser navigation according to the provided user instructions. After completing the navigation and actions, generate a Playwright test script in TypeScript that replicates the actions taken. The script must follow Playwright's best practices, including:
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

# Default user task
DEFAULT_USER_TASK = """
1. Navigate to ai.azure.com?auth=local.
2. Navigate to Model Catalogue.
3. Search for Azure Speech.
4. See if the Azure AI Speech is visible or not
5. Close the browser.
"""

async def main():
    # Get user task from command-line argument, file, or default
    if len(sys.argv) > 1:
        user_task = sys.argv[1]
    else:
        # try:
        #     with open("pr_description.txt", "r", encoding="utf-8") as f:
        #         user_task = f.read().strip()
        #         logging.info(f"Using PR description from pr_description.txt:\n{user_task}")
        # except FileNotFoundError:
        user_task = DEFAULT_USER_TASK
        # logging.info("pr_description.txt not found, using default task")

    logging.info(f"Generating Playwright script for task:\n{user_task}")

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