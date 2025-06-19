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
import chardet

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,  # Increased to DEBUG for detailed logging
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

def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding'] or 'utf-8'
        logging.info(f"Detected encoding for {file_path}: {encoding}")
        return encoding
    except Exception as e:
        logging.error(f"Error detecting encoding for {file_path}: {e}")
        return 'utf-8'

def parse_playwright_results(json_path: str) -> tuple[str, str]:
    """Parse Playwright results.json to extract errors and test script content."""
    try:
        # Detect file encoding
        encoding = detect_encoding(json_path)
        encodings_to_try = [encoding, 'utf-8-sig', 'utf-16-le', 'utf-16-be', 'utf-8']
        results = None
        for enc in encodings_to_try:
            try:
                with open(json_path, 'r', encoding=enc) as f:
                    results = json.load(f)
                logging.info(f"Successfully parsed {json_path} with encoding {enc}")
                break
            except Exception as e:
                logging.debug(f"Failed to parse {json_path} with encoding {enc}: {e}")
        
        if results is None:
            raise Exception("All encoding attempts failed")

        # Log results.json content for debugging
        logging.debug(f"results.json content: {json.dumps(results, indent=2)}")

        error_context = []
        test_script_content = ""
        test_script_path = None

        for suite in results.get('suites', []):
            # Extract test script file path
            test_script_path = suite.get('file', '')
            # Resolve relative path to tests/ directory
            if test_script_path and not os.path.isabs(test_script_path):
                test_script_path = os.path.join(TESTS_DIR, test_script_path)
                logging.debug(f"Resolved test script path to: {test_script_path}")
            for test in suite.get('tests', []):
                if test.get('status') == 'failed':
                    test_name = test.get('title', 'Unknown Test')
                    for error in test.get('errors', []):
                        message = error.get('message', '')
                        stack = error.get('stack', '')
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

        # Read the test script content if file path exists
        if test_script_path and os.path.exists(test_script_path):
            try:
                with open(test_script_path, 'r', encoding='utf-8') as f:
                    test_script_content = f.read()
                logging.info(f"Read test script content from {test_script_path}")
            except Exception as e:
                logging.error(f"Error reading test script {test_script_path}: {e}")
        elif test_script_path:
            logging.warning(f"Test script file {test_script_path} not found")
        else:
            logging.warning("No test script file path found in results.json")

        return "\n\n".join(error_context), test_script_content

    except FileNotFoundError:
        logging.info(f"{json_path} not found, proceeding with minimal script generation")
        return "", ""
    except Exception as e:
        logging.error(f"Error parsing {json_path}: {e}")
        return "", ""

async def generate_playwright_script(error_context: str, test_script_content: str) -> str:
    """Generate a fresh Playwright TypeScript test script by inferring task from the failing script."""
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

    # System prompt for task inference and script generation
    system_prompt = """
You are a Playwright test automation expert tasked with generating a fresh TypeScript test script by inferring the intended task from a failing Playwright test script and its error logs from results.json. Follow these steps:

1. **Analyze the Failing Script**:
   - Review the provided test script content to understand its intent (e.g., navigation, clicks, assertions).
   - Identify the test's purpose based on test names, comments, and Playwright commands (e.g., page.goto, locator.click, expect.toBeVisible).
   - If no script content is provided, infer a minimal task from the error context (e.g., test title, error steps).

2. **Analyze Error Context**:
   - Examine the error context from results.json to identify failing steps (e.g., outdated selectors, timeouts, missing elements).
   - Map errors to natural language steps (e.g., "Click on an element", "Wait for page to load").

3. **Infer the Task**:
   - Combine insights from the script and errors to infer the intended task (e.g., "Navigate to a page and verify an element").
   - If no script or clear errors are available, generate a generic navigation test (e.g., visit https://ai.azure.com?auth=local).

4. **Execute the Task**:
   - Use the Playwright MCP server to open a browser and perform the inferred task.
   - Record navigation, clicks, form inputs, and assertions in real-time.
   - Handle UI changes or flakiness by:
     - Using robust locators (e.g., getByRole, getByText, getByTestId).
     - Adding waits (e.g., waitForLoadState('networkidle'), expect().toBeVisible()).
     - Checking for optional popups or dialogs.

5. **Apply Healing Logic**:
   - Fix issues identified in the error context:
     - Replace outdated selectors.
     - Increase timeouts (e.g., 10000ms for navigation, 15000ms for visibility).
     - Handle dynamic page loads with waitUntil: 'networkidle' or waitForURL.
     - Do NOT mask real application bugs (e.g., missing features).
   - Ensure actions wait for elements to be visible and stable.

6. **Generate a Fresh Script**:
   - Create a new Playwright test script in TypeScript that:
     - Uses async/await syntax.
     - Imports {{ test, expect }} from '@playwright/test'.
     - Uses robust locators.
     - Includes timeouts and dynamic waits.
     - Checks for optional popups or overlays.
     - Enables trace recording (assumed enabled in playwright.config.ts).
   - Always provide the script in a ```typescript code block.

Error Context (from results.json):
{error_context}

Failing Test Script Content:
{test_script_content}
"""
    # Combine system prompt, error context, and test script content
    prompt = system_prompt.format(error_context=error_context, test_script_content=test_script_content)

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

                return sys.exit()
            
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                logging.warning(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            logging.error(f"Error running agent: {e}")

            return "Error in content-filter section"

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate healed Playwright test script")
    parser.add_argument("--results", default="results.json", help="Path to Playwright results.json")
    args = parser.parse_args()

    results_path = args.results

    # Load error context and test script content from results.json
    error_context, test_script_content = parse_playwright_results(results_path)

    logging.info("Generating Playwright script based on inferred task")

    # Generate the test script
    test_script = await generate_playwright_script(error_context, test_script_content)

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