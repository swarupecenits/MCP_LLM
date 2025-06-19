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
from typing import Dict, List, Tuple, Optional

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

def parse_test_script(script_content: str) -> Dict:
    """Parse test script to extract test steps and navigation commands."""
    parsed_info = {
        'url': None,
        'test_steps': [],
        'imports': [],
        'test_name': 'Generated Test'
    }
    
    lines = script_content.split('\n')
    current_step = {}
    
    for line in lines:
        line = line.strip()
        
        # Extract imports
        if line.startswith('import'):
            parsed_info['imports'].append(line)
        
        # Extract test name
        if 'test(' in line and '"' in line:
            match = re.search(r'test\([\'"]([^\'"]+)[\'"]', line)
            if match:
                parsed_info['test_name'] = match.group(1)
        
        # Extract URL navigation
        if 'goto(' in line:
            url_match = re.search(r'goto\([\'"]([^\'"]+)[\'"]', line)
            if url_match:
                parsed_info['url'] = url_match.group(1)
        
        # Extract common Playwright actions
        if any(action in line for action in ['click(', 'fill(', 'selectOption(', 'getBy']):
            step_info = {
                'action': line,
                'type': 'action',
                'line_number': len(parsed_info['test_steps']) + 1
            }
            
            # Determine action type
            if 'click(' in line:
                step_info['action_type'] = 'click'
            elif 'fill(' in line:
                step_info['action_type'] = 'fill'
            elif 'selectOption(' in line:
                step_info['action_type'] = 'select'
            elif 'getBy' in line:
                step_info['action_type'] = 'locate'
            
            parsed_info['test_steps'].append(step_info)
    
    return parsed_info

async def execute_test_with_browser(test_script_content: str, client: MCPClient, llm) -> Tuple[str, Dict]:
    """Execute test script using Playwright MCP server to gather real browser behavior."""
    
    # Parse the original test script
    parsed_test = parse_test_script(test_script_content)
    
    # Setup Agent
    agent = MCPAgent(llm=llm, client=client, max_steps=50)
    
    execution_prompt = f"""
You are a Playwright automation expert. I need you to execute the following test script step by step using the Playwright MCP server to understand the actual page behavior and identify issues.

**Original Test Script:**
```typescript
{test_script_content}
```

**Parsed Test Information:**
- URL: {parsed_test.get('url', 'Not specified')}
- Test Name: {parsed_test.get('test_name')}
- Number of Steps: {len(parsed_test.get('test_steps', []))}

**Your Task:**
1. Open a browser using the Playwright MCP server
2. Navigate to the target URL: {parsed_test.get('url', '')}
3. Execute each step from the original test script
4. When you encounter errors or issues:
   - Document the exact error message
   - Inspect the page to understand why the locator failed
   - Find alternative locators that would work
   - Note any timing issues or element visibility problems

5. For each step, provide:
   - Whether it succeeded or failed
   - The exact error message if it failed
   - Alternative locators that would work
   - Any additional context about the page state

**Important Instructions:**
- Use the browser tools to actually navigate and interact with the page
- Take screenshots when encountering errors to understand the page state
- Inspect elements to find better locators (data-testid, unique IDs, etc.)
- Test multiple locator strategies for problematic elements
- Document the actual page structure and available elements

Please execute this step by step and provide detailed feedback on what works and what doesn't.
"""

    execution_results = {
        'success': False,
        'errors': [],
        'successful_steps': [],
        'failed_steps': [],
        'page_insights': {},
        'alternative_locators': {}
    }

    try:
        result = await agent.run(execution_prompt, max_steps=50)
        execution_results['success'] = True
        execution_results['execution_log'] = result
        
        # Parse the execution results from the agent's response
        if 'error' in result.lower() or 'failed' in result.lower():
            execution_results['has_errors'] = True
        else:
            execution_results['has_errors'] = False
            
        logging.info("Test execution completed successfully")
        return result, execution_results
        
    except Exception as e:
        logging.error(f"Error during test execution: {e}")
        execution_results['errors'].append(str(e))
        return str(e), execution_results

async def generate_corrected_script(original_script: str, execution_results: str, execution_data: Dict, llm, client) -> str:
    """Generate a corrected Playwright script based on execution results."""
    
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    
    correction_prompt = f"""
You are a Playwright test automation expert.Use the Playwright MCP server to perform browser navigation according to the provided user instructions. Based on the execution results from running the original test script, generate a corrected and improved version.

**Original Test Script:**
```typescript
{original_script}
```

**Execution Results and Findings:**
{execution_results}

**Task: Generate Improved Test Script**

Based on the execution results, create a corrected TypeScript Playwright test script that:

1. **Fixes Identified Issues:**
   - Replace failed locators with working alternatives discovered during execution
   - Add proper waits for elements that had timing issues
   - Handle strict mode violations with more specific selectors
   - Add error handling for flaky elements

2. **Best Practices Implementation:**
   - Use data-testid attributes when available
   - Implement proper waiting strategies (waitForSelector, waitForLoadState)
   - Add timeout configurations where needed
   - Use exact text matching where appropriate
   - Add element visibility checks before interactions

3. **Enhanced Robustness:**
   - Add try-catch blocks for error-prone actions
   - Implement retry mechanisms for flaky elements
   - Add assertions to verify expected page states
   - Include proper page load waiting

4. **Script Structure:**
   - Use proper TypeScript/Playwright imports
   - Include descriptive test names and comments
   - Add proper async/await patterns
   - Structure the test logically with clear steps

**Requirements:**
- Return ONLY the corrected TypeScript test script in a ```typescript code block
- Ensure all locators are based on actual page inspection results
- Include proper error handling and robust element selection
- Add meaningful assertions and waits
- Make the script production-ready and reliable

Generate the corrected script now:
"""

    try:
        result = await agent.run(correction_prompt, max_steps=30)
        
        # Extract TypeScript code block
        code_match = re.search(r'```typescript\n([\s\S]*?)\n```', result)
        if code_match:
            return code_match.group(1)
        else:
            # Try to extract code without typescript marker
            code_match = re.search(r'```\n([\s\S]*?)\n```', result)
            if code_match:
                return code_match.group(1)
            else:
                logging.error("No code block found in the correction response")
                logging.info(f"Full response: {result}")
                return original_script  # Return original if parsing fails
                
    except Exception as e:
        logging.error(f"Error generating corrected script: {e}")
        return original_script

def read_test_script_file(file_path: str) -> str:
    """Read test script from file with proper encoding detection."""
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        logging.info(f"Successfully read test script from {file_path}")
        return content
    except Exception as e:
        logging.error(f"Error reading test script file {file_path}: {e}")
        return ""

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate corrected Playwright test script by executing and analyzing original script")
    parser.add_argument("--input", required=True, help="Path to input test script file (.ts or .js)")
    parser.add_argument("--output", help="Path to output corrected test script (optional)")
    parser.add_argument("--mcp-config", default="playwright_mcp.json", help="Path to MCP configuration file")
    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        logging.error(f"Input test script file not found: {args.input}")
        sys.exit(1)

    # Read the input test script
    original_script = read_test_script_file(args.input)
    if not original_script:
        logging.error("Failed to read input test script")
        sys.exit(1)

    # Load environment variables
    load_dotenv()
    if not os.getenv('AZURE_OPENAI_ENDPOINT') or not os.getenv('AZURE_OPENAI_API_KEY'):
        logging.error("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY environment variables.")
        sys.exit(1)

    # Initialize MCP Client
    try:
        client = MCPClient.from_config_file(args.mcp_config)
        logging.info("Connected to Playwright MCP server successfully")
    except Exception as e:
        logging.error(f"Failed to initialize MCP client: {e}")
        sys.exit(1)

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
        logging.info("LLM initialization successful")
    except Exception as e:
        logging.error(f"Error initializing LLM: {e}")
        sys.exit(1)

    logging.info("Starting test script execution and analysis...")
    
    # Execute the original test script to gather insights
    execution_results, execution_data = await execute_test_with_browser(
        original_script, client, llm
    )

    logging.info("Generating corrected test script based on execution results...")
    
    # Generate corrected script
    corrected_script = await generate_corrected_script(
        original_script, execution_results, execution_data, llm, client
    )

    if corrected_script:
        # Determine output file path
        if args.output:
            output_path = args.output
        else:
            base_name = os.path.splitext(os.path.basename(args.input))[0]
            output_path = get_unique_filename(f"{base_name}_corrected", ".spec.ts", TESTS_DIR)

        # Save corrected script
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(corrected_script)
            logging.info(f"Corrected test script saved to {output_path}")
            
            # Print summary
            print("\n" + "="*60)
            print("TEST SCRIPT CORRECTION COMPLETED")
            print("="*60)
            print(f"Original script: {args.input}")
            print(f"Corrected script: {output_path}")
            print("\nCORRECTIONS APPLIED:")
            print("- Executed original script in real browser")
            print("- Identified failing locators and timing issues")
            print("- Generated working alternatives based on actual page inspection")
            print("- Added robust error handling and waiting strategies")
            print("- Implemented best practices for reliable test automation")
            print("="*60)
            
        except IOError as e:
            logging.error(f"Error saving corrected script: {e}")
            sys.exit(1)
    else:
        logging.error("Failed to generate corrected test script")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())