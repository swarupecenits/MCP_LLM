# scripts/e2e-test-generator/parse_errors.py

import json
import os
import sys

def parse_playwright_json_report(report_path: str, output_file_path: str):
    """
    Parses a Playwright JSON report, extracts failure details, and saves them to a file.
    """
    if not os.path.exists(report_path):
        print(f"Error: Playwright report not found at {report_path}", file=sys.stderr)
        sys.exit(1)

    with open(report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)

    error_details = []
    failed_tests_count = 0

    for suite in report_data.get('suites', []):
        for spec in suite.get('specs', []):
            for test in spec.get('tests', []):
                for result in test.get('results', []):
                    if result.get('status') == 'failed':
                        failed_tests_count += 1
                        error_message = ""
                        stack_trace = ""
                        error_location = ""

                        # Playwright can have multiple errors for a single test result (e.g., retries)
                        # We'll take the first one for simplicity, or loop if you need all.
                        if result.get('errors'):
                            error = result['errors'][0]
                            error_message = error.get('message', 'No error message provided.')
                            stack_trace = error.get('stack', 'No stack trace provided.')
                            if error.get('location'):
                                loc = error['location']
                                error_location = f"File: {loc.get('file', 'N/A')}, Line: {loc.get('line', 'N/A')}, Column: {loc.get('column', 'N/A')}"

                        error_details.append(f"--- Failed Test: {test.get('title', 'Untitled Test')} ---\n")
                        error_details.append(f"Test File: {spec.get('file', 'N/A')}\n")
                        error_details.append(f"Browser: {test.get('projectName', 'N/A')}\n")
                        error_details.append(f"Status: {result.get('status', 'N/A')}\n")
                        error_details.append(f"Error Message:\n{error_message}\n")
                        if error_location:
                            error_details.append(f"Error Location: {error_location}\n")
                        if stack_trace:
                            error_details.append(f"Stack Trace:\n{stack_trace}\n")
                        error_details.append("\n")

    if failed_tests_count == 0:
        error_details.append("No failed tests found.\n")
        print("No failed tests found in the report.")
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            outfile.write("No failed tests found in the latest run.")
        sys.exit(0)
    else:
        print(f"Found {failed_tests_count} failed tests. Details saved to {output_file_path}")
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            outfile.writelines(error_details)
        sys.exit(1) # Indicate failure if there are failed tests (optional, based on pipeline logic)

if __name__ == "__main__":
    # Adjust this path based on where results.json is generated
    report_path = os.path.join(os.getcwd(), 'tests-e2e-playwright/test-results', 'local-test-results.json')
    # Output error details to this file
    output_file_path = os.path.join(os.getcwd(), 'error_details.md') # Or .txt

    parse_playwright_json_report(report_path, output_file_path)