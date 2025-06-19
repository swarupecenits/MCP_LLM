import asyncio
import os
import re
import json
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

def parse_playwright_results(json_path: str) -> str:
    """Parse Playwright results.json to extract errors and map to natural language steps."""
    try:
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            results = json.load(f)
        
        error_context = []
        for suite in results.get('suites', []):
            for test in suite.get('tests', []):
                if test.get('status') == 'failed':
                    test_name = test.get('title', 'Unknown Test')
                    for error in test.get('errors', []):
                        message = error.get('message', '')
                        stack = error.get('stack', '')
                        # Map error to natural language step
                        # Map error to natural language step for flakiness-related issues
                        message_lower = message.lower()
                        if 'locator.click' in message_lower:
                            step = "Click on an element"
                        elif 'locator.fill' in message_lower:
                            step = "Enter text in an input field"
                        elif 'locator.selectoption' in message_lower:
                            step = "Select an option from a dropdown"
                        elif 'locator.check' in message_lower or 'locator.uncheck' in message_lower:
                            step = "Check or uncheck a checkbox"
                        elif 'locator.type' in message_lower:
                            step = "Type text into an input field"
                        elif 'locator.press' in message_lower:
                            step = "Press a key on the keyboard"
                        elif 'expect.tobevisible' in message_lower:
                            step = "Verify an element is visible"
                        elif 'expect.tobehidden' in message_lower:
                            step = "Verify an element is hidden"
                        elif 'expect.tobeenabled' in message_lower:
                            step = "Verify an element is enabled"
                        elif 'expect.tobedisabled' in message_lower:
                            step = "Verify an element is disabled"
                        elif 'expect.tohavevalue' in message_lower:
                            step = "Verify an input field has a specific value"
                        elif 'expect.tohavetext' in message_lower:
                            step = "Verify an element has specific text"
                        elif 'expect.tohavecount' in message_lower:
                            step = "Verify the number of elements matching a selector"
                        elif 'timeout' in message_lower:
                            step = "Wait for page or element to load"
                        elif 'element not found' in message_lower or 'no elements found' in message_lower:
                            step = "Locate an element on the page"
                        elif 'multiple elements found' in message_lower:
                            step = "Select a specific element from multiple matches"
                        elif 'detached from the dom' in message_lower:
                            step = "Wait for element to be attached to the DOM"
                        elif 'not visible' in message_lower:
                            step = "Wait for element to become visible"
                        elif 'not enabled' in message_lower:
                            step = "Wait for element to become enabled"
                        elif 'not clickable' in message_lower or 'element is not clickable' in message_lower:
                            step = "Ensure element is clickable"
                        elif 'target closed' in message_lower:
                            step = "Handle page or browser closure"
                        elif 'navigation failed' in message_lower or 'navigation timeout' in message_lower:
                            step = "Wait for page navigation to complete"
                        elif 'network error' in message_lower or 'failed to fetch' in message_lower:
                            step = "Handle network request failure"
                        elif 'stale element' in message_lower:
                            step = "Refresh element reference before action"
                        elif 'element is covered' in message_lower or 'element is obscured' in message_lower:
                            step = "Ensure element is not covered by another element"
                        elif 'frame not found' in message_lower:
                            step = "Locate a frame or iframe"
                        elif 'dialog did not appear' in message_lower:
                            step = "Handle unexpected dialog absence"
                        elif 'unexpected dialog' in message_lower:
                            step = "Dismiss unexpected dialog"
                        elif 'viewport size' in message_lower:
                            step = "Adjust viewport settings"
                        else:
                            step = "Perform an action"
                        error_context.append(f"Error in '{test_name}': {message}\nStep: {step}\nStack: {stack}")
        
        return "\n\n".join(error_context)
    except FileNotFoundError:
        logging.info(f"{json_path} not found, proceeding without error context")
        return ""
    except Exception as e:
        logging.error(f"Error parsing {json_path}: {e}")
        return ""

async def generate_playwright_script(user_task: str, error_context: str = "") -> str:
    """Generate a Playwright TypeScript test script with healing for UI changes."""
    # Load environment variables
    load_dotenv()
    if not os.getenv('AZURE_OPENAI_ENDPOINT') or not os.getenv('AZURE_OPENAI_API_KEY'):
        logging.error("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY environment variables.")
        return ""

    # Load MCP Client from config
    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
        logging.info("Connected to MCP server successfully")
    except Exception as e2:
        logging.error(f"Failed to initialize MCP client with default configuration: {e2}")
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
        logging.info("AI Agent Initialization Successful")
    except Exception as e:
        logging.error(f"Error initializing AzureChatOpenAI: {e}")
        return ""

    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # System prompt with healing logic
    system_prompt = """
You are a Playwright test automation expert tasked with generating a TypeScript test script that accounts for recent UI changes based on error logs from Playwright's results.json. Follow these steps:

1. Analyze the provided error context to identify failing steps, such as outdated selectors, timeouts, or missing elements.
2. Convert each failing step into a natural language description (e.g., "Click on an element").
3. Apply targeted healing logic to fix common UI issues:
   - Replace outdated selectors (e.g., #old-id) with robust alternatives like getByRole, getByText, or getByTestId.
   - Increase timeouts (e.g., from 5s to 15s) for slow-loading elements.
   - Handle optional popups (e.g., consent dialogs) by checking for their presence before proceeding.
   - Ensure actions wait for elements to be visible and stable (e.g., use expect().toBeVisible() before clicking).
   - For timeouts, add waitForLoadState('networkidle') or increase timeout durations.
   - Do NOT mask real application bugs (e.g., missing features); only fix UI-related issues like selector changes or timing.
4. Generate a Playwright test script in TypeScript that:
   - Uses async/await syntax.
   - Imports {{ test, expect }} from '@playwright/test'.
   - Uses robust locators (e.g., getByRole, getByText, getByTestId).
   - Includes timeouts (e.g., 10000ms for navigation, 15000ms for visibility).
   - Handles dynamic page loads with waitUntil: 'networkidle' or waitForURL.
   - Checks for optional popups or overlays and handles them appropriately.
   - Enables trace recording (assumed enabled in playwright.config.ts).
   - Always provides the script in a ```typescript code block, even if the user task is generic.
5. If the user task is vague (e.g., "user task"), generate a minimal script based on the error context or a basic navigation test.
6. Record the actions performed during navigation and ensure the script reflects them accurately.

Error Context (from results.json):
{error_context}

User Instructions:
{user_task}
"""
    # Combine system prompt, error context, and user task
    prompt = system_prompt.format(error_context=error_context, user_task=user_task)

    # Run agent with retry logic
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
    parser = argparse.ArgumentParser(description="Generate healed Playwright test script")
    parser.add_argument("--task", required=True, help="User task describing test steps")
    parser.add_argument("--results", default="results.json", help="Path to Playwright results.json")
    args = parser.parse_args()

    user_task = args.task
    results_path = args.results

    # Load error context from results.json
    error_context = parse_playwright_results(results_path)
    if not error_context:
        logging.info("No error context provided, generating script without healing")

    logging.info(f"Generating Playwright script for task:\n{user_task}")

    # Generate the test script
    test_script = await generate_playwright_script(user_task, error_context)

    if test_script:
        # Save to tests directory
        test_file_path = get_unique_filename("self_heal_test_output", ".spec.ts", TESTS_DIR)
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_script)
            logging.info(f"Test script saved to {test_file_path}")
        except IOError as e:
            logging.error(f"Error saving test script: {e}")
            sys.exit(1)
    else:
        logging.error("Failed to generate test script")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())