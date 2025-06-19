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

def analyze_strict_mode_violations(error_message: str) -> dict:
    """Analyze strict mode violations and extract element details."""
    violation_info = {
        'is_strict_violation': False,
        'elements_found': [],
        'suggested_fixes': []
    }
    
    if 'strict mode violation' in error_message.lower():
        violation_info['is_strict_violation'] = True
        
        # Extract element information
        lines = error_message.split('\n')
        for line in lines:
            if line.strip().startswith(('1)', '2)', '3)')):
                # Extract element details
                if 'id="' in line:
                    id_match = re.search(r'id="([^"]*)"', line)
                    if id_match:
                        element_id = id_match.group(1)
                        violation_info['elements_found'].append({
                            'type': 'id',
                            'value': element_id,
                            'selector': f'#{element_id}'
                        })
                
                if 'data-automation-id="' in line:
                    auto_id_match = re.search(r'data-automation-id="([^"]*)"', line)
                    if auto_id_match:
                        auto_id = auto_id_match.group(1)
                        violation_info['elements_found'].append({
                            'type': 'data-automation-id',
                            'value': auto_id,
                            'selector': f'[data-automation-id="{auto_id}"]'
                        })
                
                if 'data-testid="' in line:
                    test_id_match = re.search(r'data-testid="([^"]*)"', line)
                    if test_id_match:
                        test_id = test_id_match.group(1)
                        violation_info['elements_found'].append({
                            'type': 'data-testid',
                            'value': test_id,
                            'selector': f'[data-testid="{test_id}"]'
                        })
        
        # Generate suggested fixes
        if violation_info['elements_found']:
            violation_info['suggested_fixes'] = [
                "Use more specific locators like getByTestId() or getByRole() with exact: true",
                "Use CSS selectors with unique identifiers",
                "Use nth() to select specific elements by index",
                "Use filter() to narrow down elements based on additional criteria"
            ]
    
    return violation_info

def parse_playwright_results(json_path: str) -> tuple[str, str, dict]:
    """Parse Playwright results.json to extract errors, test script content, and analysis."""
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

        error_context = []
        error_analysis = {}
        test_script_content = ""
        test_script_path = None

        for suite in results.get('suites', []):
            # Extract test script file path
            test_script_path = suite.get('file', '')
            # Resolve relative path to tests/ directory
            if test_script_path and not os.path.isabs(test_script_path):
                test_script_path = os.path.join(TESTS_DIR, test_script_path)
                logging.debug(f"Resolved test script path to: {test_script_path}")
            
            for spec in suite.get('specs', []):
                for test in spec.get('tests', []):
                    if test.get('status') == 'unexpected':
                        test_name = spec.get('title', 'Unknown Test')
                        for result in test.get('results', []):
                            if result.get('status') == 'failed':
                                for error in result.get('errors', []):
                                    message = error.get('message', '')
                                    
                                    # Analyze strict mode violations
                                    violation_analysis = analyze_strict_mode_violations(message)
                                    error_analysis[test_name] = violation_analysis
                                    
                                    # Map error to natural language step
                                    message_lower = message.lower()
                                    if 'strict mode violation' in message_lower:
                                        step = "Select a specific element from multiple matches using more precise locators"
                                    elif 'locator.click' in message_lower:
                                        step = "Click on an element"
                                    elif 'locator.fill' in message_lower:
                                        step = "Enter text in an input field"
                                    elif 'locator.selectoption' in message_lower:
                                        step = "Select an option from a dropdown"
                                    elif 'timeout' in message_lower:
                                        step = "Wait for page or element to load"
                                    else:
                                        step = "Perform an action"
                                    
                                    error_context.append(f"Error in '{test_name}': {message}\nStep: {step}")

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

        return "\n\n".join(error_context), test_script_content, error_analysis

    except FileNotFoundError:
        logging.info(f"{json_path} not found, proceeding with minimal script generation")
        return "", "", {}
    except Exception as e:
        logging.error(f"Error parsing {json_path}: {e}")
        return "", "", {}

async def generate_playwright_script(error_context: str, test_script_content: str, error_analysis: dict) -> str:
    """Generate a fresh Playwright TypeScript test script with enhanced error handling."""
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

    # Enhanced system prompt with specific error analysis
    system_prompt = f"""
You are a Playwright test automation expert tasked with generating a fresh, robust TypeScript test script. Based on the analysis of the failing test, you need to fix specific issues:

**ERROR ANALYSIS:**
{json.dumps(error_analysis, indent=2)}

**CRITICAL FIXES NEEDED:**

1. **Strict Mode Violations**: The main error is a strict mode violation where `getByRole('button', {{ name: 'All' }})` found 2 elements:
   - Element 1: `<button id="resourcesButton" aria-label="All resources">` (with testid="resourcesButton")
   - Element 2: `<button id="all">All</button>`

2. **Required Solutions**:
   - Use `getByTestId('resourcesButton')` for the first button
   - Use `getByRole('button', {{ name: 'All', exact: true }})` for the second button
   - Add element uniqueness checks before actions
   - Implement proper waiting strategies

3. **Enhanced Locator Strategy**:
   - Prefer data-testid attributes when available
   - Use exact text matching with `exact: true`
   - Add nth() selectors for specific element selection
   - Use filter() methods to narrow down elements

4. **Robust Error Handling**:
   - Add try-catch blocks for flaky elements
   - Implement retry mechanisms for intermittent failures
   - Use waitFor() methods before interactions
   - Add visibility and stability checks

**TASK EXECUTION:**

1. **Analyze the Intent**: The test appears to be navigating Azure AI Foundry and clicking on various buttons including "All" buttons.

2. **Execute the Corrected Task**: Use the Playwright MCP server to:
   - Navigate to the target page
   - Identify elements using robust, unique locators
   - Handle multiple elements with same text by using specific selectors
   - Add proper waits and error handling

3. **Generate the Fixed Script**: Create a TypeScript test that:
   - Uses `import {{ test, expect }} from '@playwright/test'`
   - Implements unique locators for each element
   - Adds timeout configurations (15000ms for visibility, 10000ms for actions)
   - Includes error handling and retry logic
   - Uses proper async/await patterns

**Original Error Context:**
{error_context}

**Original Test Script:**
{test_script_content}

Please execute the corrected version of this test and provide the complete, working TypeScript test script in a ```typescript code block.
"""

    # Run agent with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await agent.run(system_prompt, max_steps=30)
            # Extract TypeScript code block
            code_match = re.search(r'```typescript\n([\s\S]*?)\n```', result)
            if code_match:
                return code_match.group(1)
            else:
                logging.error("No TypeScript code block found in the agent's response")
                logging.info(f"Agent response: {result}")
                return ""
            
        except Exception as e:
            if "content_filter" in str(e).lower() and attempt < max_retries - 1:
                logging.warning(f"Content filter error on attempt {attempt + 1}: {e}. Retrying...")
                continue
            logging.error(f"Error running agent: {e}")
            return ""

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate healed Playwright test script with enhanced error analysis")
    parser.add_argument("--results", default="results.json", help="Path to Playwright results.json")
    args = parser.parse_args()

    results_path = args.results

    # Load error context, test script content, and error analysis from results.json
    error_context, test_script_content, error_analysis = parse_playwright_results(results_path)

    logging.info("Analyzing Playwright test errors...")
    
    # Log error analysis
    if error_analysis:
        logging.info("Error Analysis Results:")
        for test_name, analysis in error_analysis.items():
            logging.info(f"Test: {test_name}")
            if analysis.get('is_strict_violation'):
                logging.info("  - Strict mode violation detected")
                logging.info(f"  - Elements found: {len(analysis.get('elements_found', []))}")
                for element in analysis.get('elements_found', []):
                    logging.info(f"    - {element['type']}: {element['value']}")

    logging.info("Generating enhanced Playwright script with error fixes...")

    # Generate the test script
    test_script = await generate_playwright_script(error_context, test_script_content, error_analysis)

    if test_script:
        # Save to tests directory
        test_file_path = get_unique_filename("healed_test", ".spec.ts", TESTS_DIR)
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_script)
            logging.info(f"Enhanced test script saved to {test_file_path}")
            
            # Also log suggested fixes
            print("\n" + "="*50)
            print("SUGGESTED FIXES APPLIED:")
            print("="*50)
            print("1. Fixed strict mode violation by using specific locators")
            print("2. Added proper element uniqueness checks")
            print("3. Implemented robust waiting strategies")
            print("4. Enhanced error handling and retry logic")
            print("5. Used data-testid and exact matching where applicable")
            print("="*50)
            
        except IOError as e:
            logging.error(f"Error saving test script: {e}")
            sys.exit(1)
    else:
        logging.error("Failed to generate test script")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())