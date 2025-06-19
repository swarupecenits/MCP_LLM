import asyncio
import os
import re
import logging
import sys
import argparse
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
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
    if not user_task:
        logging.error("No user task provided. Cannot generate script.")
        return ""

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
        logging.error("Error: playwright_mcp.json not found")
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

    # System prompt for Playwright MCP server navigation and script generation
    system_prompt = """
You are a Playwright test automation expert for the Azure AI Studio workspace-portal application at https://ai.azure.com?auth=local. Use the Playwright MCP server to perform browser navigation and actions according to the provided user task. After completing the actions, generate a Playwright test script in TypeScript that replicates them. Follow these guidelines:
- Use async/await syntax.
- Import {{ test, expect }} from '@playwright/test'.
- Use robust locators (e.g., getByRole, getByText, getByTestId).
- Include timeouts (e.g., 15000ms for navigation, 10000ms for visibility checks).
- Handle dynamic page loads with waitUntil: 'networkidle' or waitForLoadState.
- Include error handling for consent popups or dialogs (e.g., check visibility before clicking).
- Ensure the script is repeatable and follows Playwright best practices.
- Provide the script in a ```typescript code block.
Record all actions performed and ensure the generated script accurately reflects them.

User Task:
{user_task}
"""
    try:
        prompt = system_prompt.format(user_task=user_task)
    except KeyError as e:
        logging.error(f"Error formatting system prompt: {e}")
        return ""

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
                logging.error("No TypeScript code block found in the agent's response.")
                return ""
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                logging.warning(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            logging.error(f"Error running agent: {e}")
            return ""

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate Playwright test script based on user task")
    parser.add_argument("--task", help="User task description or path to a file containing the task (e.g., PR description)")
    args = parser.parse_args()

    # Get user task from command-line argument or pr_description.txt
    user_task = None
    if args.task:
        if os.path.isfile(args.task):
            try:
                with open(args.task, "r", encoding="utf-8") as f:
                    user_task = f.read().strip()
                logging.info(f"Using task from file {args.task}: {user_task}")
            except IOError as e:
                logging.error(f"Error reading task file {args.task}: {e}")
                sys.exit(1)
        else:
            user_task = args.task
            logging.info(f"Using task from command-line: {user_task}")
    else:
        try:
            with open("pr_description.txt", "r", encoding="utf-8") as f:
                user_task = f.read().strip()
            logging.info(f"Using task from pr_description.txt: {user_task}")
        except FileNotFoundError:
            logging.error("PR description not found in pr_description.txt.")
            sys.exit(1)

    logging.info(f"Generating Playwright script for task: {user_task}")

    # Generate the test script
    test_script = await generate_playwright_script(user_task)

    if test_script:
        # Save to tests directory
        test_file_path = get_unique_filename("generated_test_output", ".spec.ts", TESTS_DIR)
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_script)
            logging.info(f"Test script generated and saved to {test_file_path}")
        except IOError as e:
            logging.error(f"Error saving test script: {e}")
            sys.exit(1)
    else:
        logging.error("Failed to generate test script")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())