import asyncio
import os
import re
import json
import logging
import sys
import argparse
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
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
        'suggestions': [],
        'raw_errors': []
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
                        for result in test.get('results', []):
                            if result.get('status') == 'failed':
                                error_info = result.get('error', {})
                                error_message = error_info.get('message', '')
                                error_stack = error_info.get('stack', '')
                                error_location = error_info.get('location', {})
                                
                                # Store raw error for console display
                                error_analysis['raw_errors'].append({
                                    'message': error_message,
                                    'stack': error_stack,
                                    'line': error_location.get('line', 0),
                                    'column': error_location.get('column', 0)
                                })
                                
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
                                
                                if 'timeout' in error_message.lower():
                                    error_analysis['timeout_issues'].append({
                                        'locator': extract_failed_locator(error_message),
                                        'timeout': extract_timeout_info(error_message),
                                        'expected': extract_expected_behavior(error_message)
                                    })
                                
                                if 'element(s) not found' in error_message.lower():
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
        
        error_analysis['suggestions'] = generate_error_based_suggestions(error_analysis)
        
        return error_analysis
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in {json_path}: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error parsing Playwright error JSON {json_path}: {e}")
        sys.exit(1)

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
    locator_match = re.search(r'Locator: (.+?)(?:\n|$)', error_message)
    if locator_match:
        return locator_match.group(1).strip()
    
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
        return "Try getByText('Browse Foundry Models'), page.locator('text=Browse Foundry Models'), or data-testid attributes"
    elif 'Go to full model catalog' in failed_locator:
        return "Try getByText('Go to full model catalog'), page.locator('a:has-text(\"Go to full model catalog\")'), or button/link selectors"
    elif 'searchbox' in failed_locator.lower():
        return "Try page.locator('input[type=\"search\"]'), getByPlaceholder('Search'), or getByRole('textbox')"
    else:
        return "Try data-testid, unique IDs, or CSS selectors; inspect page for stable attributes"

def generate_error_based_suggestions(error_analysis: Dict) -> List[str]:
    """Generate comprehensive suggestions based on error analysis."""
    suggestions = []
    if error_analysis['timeout_issues']:
        suggestions.extend([
            "Increase timeouts to 30000ms",
            "Add waitForLoadState('networkidle')",
            "Wait for element stability before actions"
        ])
    if error_analysis['element_not_found']:
        suggestions.extend([
            "Inspect page for actual element content",
            "Use partial text matching or CSS selectors",
            "Implement retry logic for dynamic content"
        ])
    if error_analysis['locator_failures']:
        suggestions.extend([
            "Use browser dev tools for reliable selectors",
            "Prefer data-testid or unique IDs",
            "Try CSS or XPath for complex elements"
        ])
    suggestions.append("Test locators in browser console")
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
        if line.startswith('import'):
            parsed_info['imports'].append(line)
        if 'test(' in line and '"' in line:
            match = re.search(r'test\([\'"]([^\'"]+)[\'"]', line)
            if match:
                parsed_info['test_name'] = match.group(1)
        if 'goto(' in line:
            url_match = re.search(r'goto\([\'"]([^\'"]+)[\'"]', line)
            if url_match:
                parsed_info['url'] = url_match.group(1)
        if any(action in line for action in ['click(', 'fill(', 'selectOption(', 'getBy', 'expect(']):
            step_info = {
                'action': line,
                'type': 'action',
                'line_number': len(parsed_info['test_steps']) + 1
            }
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
    locator_match = re.search(r'(getBy\w+\([^)]+\))', line)
    if locator_match:
        return locator_match.group(1)
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

def display_self_healing_analysis(error_analysis: Dict, parsed_test: Dict) -> Dict:
    """Display structured error analysis and suggested fixes."""
    print("\n" + "="*80)
    print("🔧 PLAYWRIGHT ERROR ANALYSIS AND SELF-HEALING")
    print("="*80)
    
    # Error Summary
    print("\n📊 ERROR SUMMARY:")
    print(f"   Test File: {error_analysis.get('test_file', 'Unknown')}")
    print(f"   Test Name: {error_analysis.get('test_name', 'Unknown')}")
    print(f"   Target URL: {parsed_test.get('url', 'Not specified')}")
    print(f"   Total Failed Steps: {len(error_analysis.get('failed_steps', []))}")
    print(f"   Timeout Issues: {len(error_analysis.get('timeout_issues', []))}")
    print(f"   Element Not Found: {len(error_analysis.get('element_not_found', []))}")
    print(f"   Locator Failures: {len(error_analysis.get('locator_failures', []))}")
    
    # Raw Errors
    if error_analysis['raw_errors']:
        print("\n🚫 RAW ERROR DETAILS:")
        for i, error in enumerate(error_analysis['raw_errors'], 1):
            print(f"   Error #{i}:")
            print(f"      Message: {error['message'][:100]}{'...' if len(error['message']) > 100 else ''}")
            print(f"      Line: {error['line']} (Column: {error['column']})")
            print(f"      Stack: {error['stack'][:100]}{'...' if len(error['stack']) > 100 else ''}")
    
    # Specific Issues
    if error_analysis['timeout_issues']:
        print(f"\n⏱️ TIMEOUT ISSUES ({len(error_analysis['timeout_issues'])}):")
        for i, issue in enumerate(error_analysis['timeout_issues'], 1):
            print(f"   {i}. Locator: {issue['locator']}")
            print(f"      Timeout: {issue['timeout']}ms")
            print(f"      Expected: {issue['expected']}")
    
    if error_analysis['element_not_found']:
        print(f"\n🔍 ELEMENT NOT FOUND ({len(error_analysis['element_not_found'])}):")
        for i, issue in enumerate(error_analysis['element_not_found'], 1):
            print(f"   {i}. Locator: {issue['locator']}")
            print(f"      Line: {issue['line']}")
    
    if error_analysis['locator_failures']:
        print(f"\n🎯 LOCATOR FAILURES ({len(error_analysis['locator_failures'])}):")
        for i, issue in enumerate(error_analysis['locator_failures'], 1):
            print(f"   {i}. Locator: {issue['failed_locator']}")
            print(f"      Line: {issue['line']}")
            print(f"      Suggestion: {issue['suggestion']}")
    
    # Suggested Fixes
    print("\n💡 SUGGESTED FIXES:")
    fixes_available = []
    if error_analysis['timeout_issues']:
        for issue in error_analysis['timeout_issues']:
            fixes_available.append({
                'type': 'timeout',
                'description': f"Increase timeout for {issue['locator']}",
                'code_fix': f"await page.waitForLoadState('networkidle');\nawait {issue['locator']}.waitFor({{ timeout: 30000, state: 'visible' }});"
            })
    if error_analysis['element_not_found']:
        for issue in error_analysis['element_not_found']:
            alternatives = generate_alternative_locators(issue['locator'])
            fixes_available.append({
                'type': 'element_not_found',
                'description': f"Replace locator {issue['locator']}",
                'alternatives': alternatives,
                'code_fix': generate_fallback_code(issue['locator'], alternatives)
            })
    if error_analysis['locator_failures']:
        for issue in error_analysis['locator_failures']:
            alternatives = generate_alternative_locators(issue['failed_locator'])
            fixes_available.append({
                'type': 'locator_failure',
                'description': f"Fix locator {issue['failed_locator']}",
                'alternatives': alternatives,
                'code_fix': generate_fallback_code(issue['failed_locator'], alternatives)
            })
    
    for i, suggestion in enumerate(error_analysis['suggestions'], 1):
        print(f"   {i}. {suggestion}")
    
    # Display Fix Previews
    if fixes_available:
        print("\n🔧 PROPOSED CODE FIXES:")
        for i, fix in enumerate(fixes_available, 1):
            print(f"   Fix #{i}: {fix['description']}")
            print(f"      Type: {fix['type']}")
            print(f"      Code Preview: {fix['code_fix'][:100]}{'...' if len(fix['code_fix']) > 100 else ''}")
    
    # For pipeline, apply all fixes automatically
    return {'apply_fixes': fixes_available, 'apply_all': True}

def generate_alternative_locators(failed_locator: str) -> List[str]:
    """Generate alternative locators based on the failed one."""
    alternatives = []
    if 'Browse Foundry Models' in failed_locator:
        alternatives = [
            "page.getByRole('link', { name: 'Browse Foundry Models' })",
            "page.locator('a:has-text(\"Browse Foundry Models\")')",
            "page.getByText('Browse Foundry Models')"
        ]
    elif 'search' in failed_locator.lower():
        alternatives = [
            "page.getByRole('textbox', { name: /search/i })",
            "page.locator('input[type=\"search\"]')",
            "page.getByPlaceholder(/search/i)"
        ]
    else:
        alternatives = [
            f"page.getByText('{failed_locator}')",
            f"page.locator('[data-testid*=\"{failed_locator.lower()}\"]')",
            f"page.getByRole('button', {{ name: /{failed_locator}/i }})"
        ]
    return alternatives

def generate_fallback_code(original_locator: str, alternatives: List[str]) -> str:
    """Generate fallback code with multiple locator strategies."""
    code = f"""async function findElement(page) {{
  const locators = [
"""
    for alt in alternatives:
        code += f"    '{alt}',\n"
    code += f"""  ];
  for (const locator of locators) {{
    try {{
      const element = {alternatives[0] if alternatives else 'page.locator(locator)'};
      await element.waitFor({{ timeout: 10000, state: 'visible' }});
      console.log(`Found element using: ${{locator}}`);
      return element;
    }} catch (e) {{
      console.log(`Failed locator: ${{locator}} - ${{e.message}}`);
    }}
  }}
  throw new Error('All locators failed for: {original_locator}');
}}"""
    return code

def validate_script(script: str) -> bool:
    """Validate TypeScript test script for basic correctness."""
    return 'import' in script and 'test(' in script and 'from' in script

async def generate_self_healed_script(original_script: str, error_analysis: Dict, healing_decisions: Dict, llm) -> str:
    """Generate a self-healed script using LLM."""
    parsed_test = parse_test_script(original_script)
    
    healing_prompt = f"""
You are an expert Playwright test automation engineer. Generate a self-healed, production-ready TypeScript test script based on the error analysis and healing decisions.

**ORIGINAL FAILING SCRIPT:**
```typescript
{original_script}
```

**ERROR ANALYSIS:**
```json
{json.dumps(error_analysis, indent=2)}
```

**HEALING DECISIONS:**
```json
{json.dumps(healing_decisions, indent=2)}
```

**REQUIREMENTS:**
1. Fix all identified issues:
   - Replace failed locators with robust fallback strategies
   - Set timeouts to 30000ms minimum
   - Add error handling with clear messages
   - Use multiple locator strategies
2. Implement self-healing:
   - Fallback locators
   - Retry mechanisms
   - Dynamic waits (networkidle, domcontentloaded)
   - Element stability checks
3. Enhance robustness:
   - Page load state management
   - Element visibility checks
   - Comprehensive logging
   - Graceful error handling
4. Apply specific fixes:
   - {', '.join([fix['description'] for fix in healing_decisions.get('apply_fixes', [])])}

**OUTPUT:**
Return ONLY the complete TypeScript test script in a ```typescript block.
"""

    try:
        from langchain.schema import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=healing_prompt)])
        result = response.content
        
        code_match = re.search(r'```typescript\n([\s\S]*?)\n```', result)
        if code_match:
            healed_script = code_match.group(1).strip()
            if validate_script(healed_script):
                return healed_script
        logging.error("Invalid or missing TypeScript code in LLM response")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error generating self-healed script: {e}")
        sys.exit(1)

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
        sys.exit(1)

def save_healed_script(script_content: str, original_filename: str) -> str:
    """Save the healed script with a descriptive filename."""
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    healed_filename = get_unique_filename(f"{base_name}_healed", ".spec.ts", TESTS_DIR)
    
    try:
        with open(healed_filename, 'w', encoding='utf-8') as f:
            f.write(script_content)
        logging.info(f"Healed script saved: {healed_filename}")
        return healed_filename
    except Exception as e:
        logging.error(f"Error saving healed script: {e}")
        sys.exit(1)

async def generate_test_from_task(task: str, llm) -> str:
    """Generate a new Playwright test script based on a task description."""
    prompt = f"""
You are an expert Playwright test automation engineer. Generate a production-ready TypeScript test script for the following task:

**TASK DESCRIPTION:**
{task}

**REQUIREMENTS:**
1. Use Playwright with TypeScript
2. Include robust locators (getByRole, getByText, data-testid)
3. Set timeouts to 30000ms
4. Add waitForLoadState('networkidle')
5. Include error handling and logging
6. Structure tests with clear steps
7. Target URL: https://mcp-use.azuresynapse.net/en-US/
8. Follow Playwright best practices

**OUTPUT:**
Return ONLY the complete TypeScript test script in a ```typescript block.
"""

    try:
        from langchain.schema import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = response.content
        
        code_match = re.search(r'```typescript\n([\s\S]*?)\n```', result)
        if code_match:
            test_script = code_match.group(1).strip()
            if validate_script(test_script):
                return test_script
        logging.error("Invalid or missing TypeScript code in LLM response")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error generating test script: {e}")
        sys.exit(1)

async def main():
    parser = argparse.ArgumentParser(description="Playwright test script generator and self-healer")
    parser.add_argument("--task", help="User task description or path to a file containing the task (e.g., PR description)")
    parser.add_argument("--test-script", help="Path to the failing test script")
    parser.add_argument("--error-json", help="Path to the Playwright error JSON file")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Validate inputs
    if not args.task and not (args.test_script and args.error_json):
        logging.error("Must provide either --task or both --test-script and --error-json")
        sys.exit(1)
    
    if args.test_script and not args.error_json or args.error_json and not args.test_script:
        logging.error("Both --test-script and --error-json are required for self-healing")
        sys.exit(1)
    
    # Initialize LLM
    llm = AzureChatOpenAI(
            model="gpt-4o",
            azure_deployment="gpt-4o",
            api_version="2023-07-01-preview",
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            api_key=SecretStr(os.getenv('AZURE_OPENAI_API_KEY', '')),
            temperature=0,
        )
    
    if args.task:
        # Handle test generation from task
        user_task = None
        if os.path.isfile(args.task):
            user_task = read_file_with_encoding(args.task).strip()
            logging.info(f"Using task from file {args.task}: {user_task}")
        else:
            user_task = args.task.strip()
            logging.info(f"Using task from command-line: {user_task}")
        
        logging.info("Generating new test script from task...")
        test_script = await generate_test_from_task(user_task, llm)
        output_file = get_unique_filename("generated_test_output", ".spec.ts", TESTS_DIR)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(test_script)
            logging.info(f"Generated test script saved: {output_file}")
        except Exception as e:
            logging.error(f"Error saving test script: {e}")
            sys.exit(1)
    
    if args.test_script and args.error_json:
        # Handle self-healing
        if not os.path.exists(args.test_script):
            logging.error(f"Test script file not found: {args.test_script}")
            sys.exit(1)
        if not os.path.exists(args.error_json):
            logging.error(f"Error JSON file not found: {args.error_json}")
            sys.exit(1)
        
        logging.info("Reading and analyzing files...")
        original_script = read_file_with_encoding(args.test_script)
        error_analysis = parse_playwright_error_json(args.error_json)
        parsed_test = parse_test_script(original_script)
        
        logging.info("Performing self-healing analysis...")
        healing_decisions = display_self_healing_analysis(error_analysis, parsed_test)
        
        if healing_decisions is None:
            logging.info("Self-healing process cancelled")
            sys.exit(0)
        
        logging.info("Generating self-healed script...")
        healed_script = await generate_self_healed_script(
            original_script, error_analysis, healing_decisions, llm
        )
        
        saved_file = save_healed_script(healed_script, args.test_script)
        if saved_file:
            print(f"\n✅ SELF-HEALING COMPLETE!")
            print(f"   Original: {args.test_script}")
            print(f"   Healed: {saved_file}")

if __name__ == "__main__":
    asyncio.run(main())
