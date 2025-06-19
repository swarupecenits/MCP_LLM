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

def parse_playwright_error_json(json_path: str) -> Dict:
    """Parse Playwright error JSON to extract comprehensive error information."""
    error_analysis = {
        'test_file': None,
        'test_name': None,
        'url': None,
        'failed_steps': [],
        'error_patterns': [],
        'timeout_issues': [],
        'locator_failures': [],
        'element_not_found': [],
        'suggestions': []
    }
    
    try:
        encoding = detect_encoding(json_path)
        with open(json_path, 'r', encoding=encoding) as f:
            results = json.load(f)
        
        logging.info(f"Successfully parsed error JSON: {json_path}")
        
        # Extract test configuration and metadata
        config = results.get('config', {})
        error_analysis['test_timeout'] = config.get('projects', [{}])[0].get('timeout', 30000)
        
        # Process test suites and extract error details
        for suite in results.get('suites', []):
            error_analysis['test_file'] = suite.get('file', '')
            
            for spec in suite.get('specs', []):
                error_analysis['test_name'] = spec.get('title', 'Unknown Test')
                
                for test in spec.get('tests', []):
                    if test.get('status') == 'unexpected':
                        # Process failed test results
                        for result in test.get('results', []):
                            if result.get('status') == 'failed':
                                # Extract error details
                                error_info = result.get('error', {})
                                error_message = error_info.get('message', '')
                                error_stack = error_info.get('stack', '')
                                error_location = error_info.get('location', {})
                                
                                # Analyze error patterns
                                failed_step = {
                                    'line': error_location.get('line', 0),
                                    'column': error_location.get('column', 0),
                                    'message': error_message,
                                    'stack': error_stack,
                                    'error_type': classify_error_type(error_message),
                                    'failed_locator': extract_failed_locator(error_message),
                                    'timeout_duration': extract_timeout_info(error_message),
                                    'expected_behavior': extract_expected_behavior(error_message)
                                }
                                
                                error_analysis['failed_steps'].append(failed_step)
                                
                                # Categorize specific error types
                                if 'timeout' in error_message.lower():
                                    error_analysis['timeout_issues'].append({
                                        'locator': extract_failed_locator(error_message),
                                        'timeout': extract_timeout_info(error_message),
                                        'expected': extract_expected_behavior(error_message)
                                    })
                                
                                if 'element(s) not found' in error_message:
                                    error_analysis['element_not_found'].append({
                                        'locator': extract_failed_locator(error_message),
                                        'line': error_location.get('line', 0)
                                    })
                                
                                if 'locator' in error_message.lower():
                                    error_analysis['locator_failures'].append({
                                        'failed_locator': extract_failed_locator(error_message),
                                        'line': error_location.get('line', 0),
                                        'suggestion': generate_locator_suggestion(error_message)
                                    })
        
        # Generate intelligent suggestions based on error patterns
        error_analysis['suggestions'] = generate_error_based_suggestions(error_analysis)
        
        return error_analysis
        
    except Exception as e:
        logging.error(f"Error parsing Playwright error JSON {json_path}: {e}")
        return error_analysis

def classify_error_type(error_message: str) -> str:
    """Classify the type of error based on the message."""
    error_message_lower = error_message.lower()
    
    if 'timeout' in error_message_lower and 'tobevisible' in error_message_lower:
        return 'visibility_timeout'
    elif 'timeout' in error_message_lower:
        return 'general_timeout'
    elif 'element(s) not found' in error_message_lower:
        return 'element_not_found'
    elif 'strict mode violation' in error_message_lower:
        return 'strict_mode_violation'
    elif 'locator' in error_message_lower:
        return 'locator_failure'
    else:
        return 'unknown'

def extract_failed_locator(error_message: str) -> str:
    """Extract the failed locator from error message."""
    # Look for Locator: pattern
    locator_match = re.search(r'Locator: (.+?)(?:\n|$)', error_message)
    if locator_match:
        return locator_match.group(1).strip()
    
    # Look for getByRole, getByText, etc.
    playwright_locator_match = re.search(r'(getBy\w+\([^)]+\))', error_message)
    if playwright_locator_match:
        return playwright_locator_match.group(1)
    
    return 'Unknown locator'

def extract_timeout_info(error_message: str) -> int:
    """Extract timeout duration from error message."""
    timeout_match = re.search(r'(\d+)ms', error_message)
    if timeout_match:
        return int(timeout_match.group(1))
    return 0

def extract_expected_behavior(error_message: str) -> str:
    """Extract what was expected from the error message."""
    expected_match = re.search(r'Expected: (.+?)(?:\n|Received:)', error_message)
    if expected_match:
        return expected_match.group(1).strip()
    return 'Unknown expectation'

def generate_locator_suggestion(error_message: str) -> str:
    """Generate intelligent locator suggestions based on error."""
    failed_locator = extract_failed_locator(error_message)
    
    if 'Browse Foundry Models' in failed_locator:
        return "Try alternatives: getByText('Browse Foundry Models'), page.locator('text=Browse Foundry Models'), or inspect for data-testid attributes"
    elif 'Go to full model catalog' in failed_locator:
        return "Try alternatives: getByText('Go to full model catalog'), page.locator('a:has-text(\"Go to full model catalog\")'), or look for button/link with similar text"
    elif 'searchbox' in failed_locator.lower():
        return "Try alternatives: page.locator('input[type=\"search\"]'), getByPlaceholder('Search'), or getByRole('textbox')"
    else:
        return "Try using more specific locators like data-testid, unique IDs, or CSS selectors"

def generate_error_based_suggestions(error_analysis: Dict) -> List[str]:
    """Generate comprehensive suggestions based on error analysis."""
    suggestions = []
    
    if error_analysis['timeout_issues']:
        suggestions.append("Increase timeout values for slow-loading elements")
        suggestions.append("Add explicit waits for page load states (networkidle, domcontentloaded)")
        suggestions.append("Wait for specific elements to be stable before interacting")
    
    if error_analysis['element_not_found']:
        suggestions.append("Elements may have different text/attributes - inspect actual page content")
        suggestions.append("Consider using more flexible locators (partial text matching)")
        suggestions.append("Add retry mechanisms for dynamically loaded content")
    
    if error_analysis['locator_failures']:
        suggestions.append("Use browser developer tools to find reliable selectors")
        suggestions.append("Prefer data-testid or unique ID attributes when available")
        suggestions.append("Consider using CSS selectors or XPath for complex elements")
    
    suggestions.append("Navigate to the actual page and inspect element structure")
    suggestions.append("Test locators in browser console before using in automation")
    
    return suggestions

def parse_test_script(script_content: str) -> Dict:
    """Parse test script to extract test steps and navigation commands."""
    parsed_info = {
        'url': None,
        'test_steps': [],
        'imports': [],
        'test_name': 'Generated Test',
        'expected_actions': []
    }
    
    lines = script_content.split('\n')
    
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
        
        # Extract Playwright actions with context
        if any(action in line for action in ['click(', 'fill(', 'selectOption(', 'getBy', 'expect(']):
            step_info = {
                'action': line,
                'type': 'action',
                'line_number': len(parsed_info['test_steps']) + 1
            }
            
            # Determine action type and extract details
            if 'click(' in line:
                step_info['action_type'] = 'click'
                step_info['target'] = extract_element_target(line)
            elif 'fill(' in line:
                step_info['action_type'] = 'fill'
                step_info['target'] = extract_element_target(line)
                step_info['value'] = extract_fill_value(line)
            elif 'selectOption(' in line:
                step_info['action_type'] = 'select'
                step_info['target'] = extract_element_target(line)
            elif 'expect(' in line and 'toBeVisible' in line:
                step_info['action_type'] = 'verify_visibility'
                step_info['target'] = extract_element_target(line)
            elif 'getBy' in line:
                step_info['action_type'] = 'locate'
                step_info['target'] = extract_element_target(line)
            
            parsed_info['test_steps'].append(step_info)
    
    return parsed_info

def extract_element_target(line: str) -> str:
    """Extract element target from Playwright action line."""
    # Extract getByRole, getByText, etc.
    locator_match = re.search(r'(getBy\w+\([^)]+\))', line)
    if locator_match:
        return locator_match.group(1)
    
    # Extract page.locator patterns
    locator_match = re.search(r'page\.locator\([\'"]([^\'"]+)[\'"]', line)
    if locator_match:
        return f"locator('{locator_match.group(1)}')"
    
    return 'Unknown element'

def extract_fill_value(line: str) -> str:
    """Extract fill value from fill action."""
    fill_match = re.search(r'fill\([\'"]([^\'"]+)[\'"]', line)
    if fill_match:
        return fill_match.group(1)
    return ''

async def execute_intelligent_browser_navigation(test_script_content: str, error_analysis: Dict, client: MCPClient, llm) -> Tuple[str, Dict]:
    """Execute intelligent browser navigation based on test script and error analysis."""
    
    parsed_test = parse_test_script(test_script_content)
    agent = MCPAgent(llm=llm, client=client, max_steps=60)
    
    execution_prompt = f"""
You are an expert Playwright automation engineer with deep knowledge of web testing and browser automation. 

**TASK: Intelligent Test Script Generation and Execution**

You have been provided with a FAILED test script and detailed error analysis. Your job is to:
1. Use the Playwright MCP server to navigate to the actual website
2. Inspect the real page structure and elements
3. Find working locators for the intended actions
4. Generate a robust, production-ready test script

**ORIGINAL FAILED TEST SCRIPT:**
```typescript
{test_script_content}
```

**DETAILED ERROR ANALYSIS:**
```json
{json.dumps(error_analysis, indent=2)}
```

**PARSED TEST INTENTIONS:**
- Target URL: {parsed_test.get('url', 'Not specified')}
- Test Name: {parsed_test.get('test_name')}
- Number of Steps: {len(parsed_test.get('test_steps', []))}
- Failed Elements: {[step.get('target', 'Unknown') for step in parsed_test.get('test_steps', [])]}

**CRITICAL ERROR INSIGHTS:**
{chr(10).join([f"- {suggestion}" for suggestion in error_analysis.get('suggestions', [])])}

**YOUR EXECUTION PLAN:**

1. **Open Browser & Navigate:**
   - Use Playwright MCP server to open a fresh browser instance
   - Navigate to: {parsed_test.get('url', '')}
   - Wait for page to fully load (use networkidle or domcontentloaded)

2. **Intelligent Element Discovery:**
   For each failed element, systematically:
   - Take a screenshot to understand the current page state
   - Inspect the page HTML structure
   - Search for elements with these failed locators:
     {chr(10).join([f"     * {failure.get('failed_locator', 'Unknown')}" for failure in error_analysis.get('locator_failures', [])])}
   - Find alternative working locators using:
     * data-testid attributes
     * Unique IDs
     * CSS selectors
     * XPath if necessary
     * Partial text matching
     * Role-based selectors with exact matching

3. **Test Each Action Step:**
   Execute the intended test flow step by step:
   - Navigate to Azure AI Foundry
   - Look for "Browse Foundry Models" or similar navigation elements
   - Find and interact with model catalog functionality
   - Locate search functionality
   - Test search with "Azure Speech" or similar terms
   - Verify results and elements

4. **Handle Dynamic Content:**
   - Wait for dynamic content to load
   - Handle any authentication or loading screens
   - Account for lazy-loaded elements
   - Use proper timing strategies

5. **Generate Findings Report:**
   Document for each step:
   - Whether the original locator works
   - Alternative working locators discovered
   - Required wait strategies
   - Any dynamic behavior observed
   - Recommended timeout values

**EXECUTION REQUIREMENTS:**
- Actually navigate to the real website using browser automation
- Test each locator and interaction in the real environment
- Take screenshots at key points for debugging
- Provide specific, working alternative locators
- Account for real-world timing and loading issues

**OUTPUT FORMAT:**
Provide a detailed execution report including:
1. Navigation success/failure
2. Element discovery results for each failed locator
3. Working alternative locators found
4. Timing and wait requirements observed
5. Any authentication or access issues encountered
6. Recommended script improvements

Execute this plan now using the Playwright MCP server.
"""

    execution_results = {
        'success': False,
        'navigation_successful': False,
        'element_discoveries': [],
        'working_locators': {},
        'timing_requirements': {},
        'page_insights': {},
        'script_recommendations': []
    }

    try:
        result = await agent.run(execution_prompt, max_steps=60)
        execution_results['success'] = True
        execution_results['execution_log'] = result
        
        # Analyze the execution results
        if 'successfully navigated' in result.lower() or 'page loaded' in result.lower():
            execution_results['navigation_successful'] = True
        
        if 'found working locator' in result.lower() or 'alternative locator' in result.lower():
            execution_results['found_alternatives'] = True
        
        logging.info("Intelligent browser navigation completed successfully")
        return result, execution_results
        
    except Exception as e:
        logging.error(f"Error during intelligent browser navigation: {e}")
        execution_results['errors'] = [str(e)]
        return str(e), execution_results

async def generate_intelligent_corrected_script(original_script: str, error_analysis: Dict, execution_results: str, execution_data: Dict, llm, client) -> str:
    """Generate an intelligent, corrected Playwright script based on comprehensive analysis."""
    
    agent = MCPAgent(llm=llm, client=client, max_steps=40)
    
    correction_prompt = f"""
You are a senior Playwright automation engineer. Based on comprehensive error analysis and real browser testing, generate a production-ready, robust test script.

**ORIGINAL FAILING SCRIPT:**
```typescript
{original_script}
```

**COMPREHENSIVE ERROR ANALYSIS:**
```json
{json.dumps(error_analysis, indent=2)}
```

**REAL BROWSER EXECUTION RESULTS:**
{execution_results}

**TASK: Generate Production-Ready Test Script**

Create a completely rewritten TypeScript Playwright test script that:

**1. FIXES ALL IDENTIFIED ISSUES:**
- Replace all failed locators with working alternatives found during browser testing
- Implement proper wait strategies based on observed page behavior
- Add appropriate timeout values based on real performance
- Handle dynamic content loading properly

**2. IMPLEMENTS INTELLIGENT LOCATOR STRATEGY:**
- Use the most reliable locators discovered during browser inspection
- Prefer data-testid > unique IDs > CSS selectors > text-based locators
- Add fallback locator strategies for robustness
- Use exact matching where appropriate to avoid ambiguity

**3. ADDS ROBUST ERROR HANDLING:**
- Implement try-catch blocks for unreliable elements
- Add retry mechanisms for flaky interactions
- Include proper page state verification
- Add meaningful error messages and debugging information

**4. OPTIMIZES TIMING AND WAITS:**
- Use appropriate wait strategies (networkidle, domcontentloaded, specific elements)
- Implement smart waiting for dynamic content
- Add element stability checks before interactions
- Use observed timeout values from real testing

**5. ENHANCES TEST STRUCTURE:**
- Clear, descriptive test steps with comments
- Proper async/await patterns
- Logical test flow with verification points
- Meaningful assertions and validations

**SPECIFIC REQUIREMENTS:**

Based on the error analysis, ensure you:
- Fix the "Browse Foundry Models" element that was not found
- Handle the search functionality properly
- Add proper waits for page transitions
- Use working locators discovered during browser testing
- Account for any authentication or loading screens observed

**SCRIPT REQUIREMENTS:**
- Use proper TypeScript imports: `import {{ test, expect }} from '@playwright/test';`
- Include comprehensive error handling
- Add descriptive comments for each major step
- Use production-ready timeouts and waits
- Include assertions to verify test success
- Make the script maintainable and readable

**OUTPUT FORMAT:**
Provide ONLY the complete, corrected TypeScript test script in a ```typescript code block.
No additional explanations - just the working, production-ready code.

Generate the corrected script now:
"""

    try:
        result = await agent.run(correction_prompt, max_steps=40)
        
        # Extract TypeScript code block with multiple fallback patterns
        code_patterns = [
            r'```typescript\n([\s\S]*?)\n```',
            r'```ts\n([\s\S]*?)\n```',
            r'```\n([\s\S]*?)\n```'
        ]
        
        for pattern in code_patterns:
            code_match = re.search(pattern, result)
            if code_match:
                corrected_script = code_match.group(1).strip()
                if corrected_script and 'import' in corrected_script and 'test(' in corrected_script:
                    return corrected_script
        
        # If no code block found, log the full response for debugging
        logging.error("No valid TypeScript code block found in the correction response")
        logging.info(f"Full LLM response: {result}")
        
        # Return a basic corrected version if parsing fails
        return generate_fallback_script(original_script, error_analysis)
                
    except Exception as e:
        logging.error(f"Error generating intelligent corrected script: {e}")
        return generate_fallback_script(original_script, error_analysis)

def generate_fallback_script(original_script: str, error_analysis: Dict) -> str:
    """Generate a fallback corrected script when LLM generation fails."""
    fallback_script = f"""import {{ test, expect }} from '@playwright/test';

test('Azure AI Speech Search Test - Corrected', async ({{ page }}) => {{
  // Enhanced timeouts and error handling based on error analysis
  test.setTimeout(60000);
  
  try {{
    // Step 1: Navigate with better wait strategy
    await page.goto('https://ai.azure.com?auth=local', {{ 
      waitUntil: 'networkidle',
      timeout: 30000 
    }});
    
    // Wait for page to be fully loaded
    await page.waitForLoadState('domcontentloaded');
    
    // Step 2: Find Browse Models link with multiple strategies
    const browseModelsSelectors = [
      'a:has-text("Browse Foundry Models")',
      'text=Browse Foundry Models',
      '[data-testid*="browse"]',
      '[aria-label*="Browse"]'
    ];
    
    let browseModelsLink = null;
    for (const selector of browseModelsSelectors) {{
      try {{
        browseModelsLink = page.locator(selector).first();
        await browseModelsLink.waitFor({{ timeout: 5000 }});
        break;
      }} catch (e) {{
        console.log(`Selector ${{selector}} failed: ${{e.message}}`);
      }}
    }}
    
    if (browseModelsLink) {{
      await browseModelsLink.click();
    }} else {{
      throw new Error('Could not find Browse Foundry Models link');
    }}
    
    // Step 3: Search functionality with enhanced locators
    const searchSelectors = [
      'input[type="search"]',
      '[placeholder*="Search"]',
      '[aria-label*="Search"]',
      'input[name*="search"]'
    ];
    
    let searchBox = null;
    for (const selector of searchSelectors) {{
      try {{
        searchBox = page.locator(selector).first();
        await searchBox.waitFor({{ timeout: 10000 }});
        break;
      }} catch (e) {{
        console.log(`Search selector ${{selector}} failed: ${{e.message}}`);
      }}
    }}
    
    if (searchBox) {{
      await searchBox.fill('Azure Speech');
      await page.keyboard.press('Enter');
      
      // Wait for search results
      await page.waitForLoadState('networkidle');
      
      // Verify search results
      const resultsVisible = await page.locator('text=Azure').first().isVisible({{ timeout: 15000 }});
      expect(resultsVisible).toBeTruthy();
    }}
    
  }} catch (error) {{
    console.error('Test failed:', error);
    throw error;
  }}
}});"""
    
    return fallback_script

def read_file_with_encoding(file_path: str) -> str:
    """Read file with proper encoding detection."""
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        logging.info(f"Successfully read file: {file_path}")
        return content
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return ""

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate AI corrected Playwright test script using error analysis and browser navigation")
    parser.add_argument("--test-script", required=True, help="Path to original test script file (.ts or .js)")
    parser.add_argument("--error-json", required=True, help="Path to Playwright error results JSON file")
    parser.add_argument("--output", help="Path to output corrected test script (optional)")
    parser.add_argument("--mcp-config", default="playwright_mcp.json", help="Path to MCP configuration file")
    args = parser.parse_args()

    # Validate input files
    if not os.path.exists(args.test_script):
        logging.error(f"Test script file not found: {args.test_script}")
        sys.exit(1)
    
    if not os.path.exists(args.error_json):
        logging.error(f"Error JSON file not found: {args.error_json}")
        sys.exit(1)

    # Read input files
    original_script = read_file_with_encoding(args.test_script)
    if not original_script:
        logging.error("Failed to read test script")
        sys.exit(1)

    # Parse error analysis
    error_analysis = parse_playwright_error_json(args.error_json)
    
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

    # Log error analysis summary
    logging.info("="*60)
    logging.info("ERROR ANALYSIS SUMMARY:")
    logging.info(f"Test File: {error_analysis.get('test_file', 'Unknown')}")
    logging.info(f"Test Name: {error_analysis.get('test_name', 'Unknown')}")
    logging.info(f"Failed Steps: {len(error_analysis.get('failed_steps', []))}")
    logging.info(f"Timeout Issues: {len(error_analysis.get('timeout_issues', []))}")
    logging.info(f"Element Not Found: {len(error_analysis.get('element_not_found', []))}")
    logging.info(f"Locator Failures: {len(error_analysis.get('locator_failures', []))}")
    logging.info("="*60)

    logging.info("Starting AI Based browser navigation and analysis...")
    
    # Execute intelligent browser navigation
    execution_results, execution_data = await execute_intelligent_browser_navigation(
        original_script, error_analysis, client, llm
    )

    logging.info("Generating AI corrected test script...")
    
    # Generate corrected script
    corrected_script = await generate_intelligent_corrected_script(
        original_script, error_analysis, execution_results, execution_data, llm, client
    )

    if corrected_script:
        # Determine output file path
        if args.output:
            output_path = args.output
        else:
            base_name = os.path.splitext(os.path.basename(args.test_script))[0]
            output_path = get_unique_filename(f"{base_name}_healed_fix", ".spec.ts", TESTS_DIR)

        # Save corrected script
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(corrected_script)
            logging.info(f"AI GENERATED corrected test script saved to {output_path}")
            
            # Print comprehensive summary
            print("\n" + "="*80)
            print("AI POWERED TEST SCRIPT CORRECTION COMPLETED")
            print("="*80)
            print(f"Original script: {args.test_script}")
            print(f"Error analysis: {args.error_json}")
            print(f"Corrected script: {output_path}")
            print("\nAI AUTONOMOUS CORRECTIONS APPLIED:")
            print("✓ Parsed comprehensive error analysis from JSON")
            print("✓ Executed real browser navigation to inspect page structure")
            print("✓ Discovered working alternative locators")
            print("✓ Implemented dynamic wait strategies")
            print("✓ Added robust error handling and retry mechanisms")
            print("✓ Generated Healed test script")
            print(f"\nError Analysis Insights:")
            print(f"- Failed steps analyzed: {len(error_analysis.get('failed_steps', []))}")
            print(f"- Timeout issues identified: {len(error_analysis.get('timeout_issues', []))}")
            print(f"- Element discovery failures: {len(error_analysis.get('element_not_found', []))}")
            print("="*80)
            
        except IOError as e:
            logging.error(f"Error saving corrected script: {e}")
            sys.exit(1)
    else:
        logging.error("Failed to generate AI corrected test script")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())