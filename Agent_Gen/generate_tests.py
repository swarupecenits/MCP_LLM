import os
from os import environ, getenv
import re
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, AzureCliCredential
from typing import Any, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

mi_client_id = getenv("CLIENT_ID")

# Initialize client
endpoint = environ["PROJECT_ENDPOINT"]
model_deployment_name = environ["MODEL_DEPLOYMENT_NAME"]
playwright_connection_id = getenv("PLAYWRIGHT_CONNECTION_ID")
agent_id = getenv("BROWSER_AGENT_ID")

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

def read_pr_description(pr_file_path: str) -> str:
    """Read the task description from pr_description.txt."""
    try:
        with open(pr_file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                raise ValueError("pr_description.txt is empty")
            return content
    except FileNotFoundError:
        print(f"Error: {pr_file_path} not found")
        raise
    except IOError as e:
        print(f"Error reading {pr_file_path}: {e}")
        raise
    except ValueError as e:
        print(f"Error: {e}")
        raise

def main(pr_file_path: str):
    """Main function to generate Playwright test script from PR description."""
    # Read task description from pr_description.txt
    try:
        task_description = read_pr_description(pr_file_path)
        print(f"Task description loaded from {pr_file_path}:\n{task_description}")
    except Exception as e:
        print(f"Failed to load task description: {e}")
        return

    with AgentsClient(
        endpoint=endpoint,
        credential=AzureCliCredential(),  # Using AzureCliCredential as per original
    ) as agents_client:
        # Browser automation tool setup
        browser_automation_tool_definition: Dict[str, Any] = {
            "type": "browser_automation",
            "browser_automation": {
                "connection": {
                    "id": playwright_connection_id,
                }
            }
        }

        # Get agent from the Azure AI Foundry
        if agent_id is None:
            raise ValueError("BROWSER_AGENT_ID environment variable is not set.")
        agent = agents_client.get_agent(agent_id)
        print(f"Using existing agent: {agent.id}")

        # Create a thread
        thread = agents_client.threads.create()
        print(f"Created thread, thread ID: {thread.id}")

        # Create a message
        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=task_description,
        )
        print(f"Created message, message ID: {message.id}")

        # Process the run
        run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            exit(1)

        # Get messages from the thread
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        
        # Extract the generated test script
        test_script = None
        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                last_text = msg.text_messages[-1].text.value
                # Look for code block with JavaScript/TypeScript content
                code_match = re.search(r'```(?:javascript|typescript)\n([\s\S]*?)\n```', last_text)
                if code_match:
                    test_script = code_match.group(1)
                    break

        if test_script:
            # Add TypeScript type annotations (minimal, as Playwright types are inferred)
            typescript_script = f"""{test_script}"""
            # Save to tests directory
            test_file_path = get_unique_filename("generated_test_output", ".spec.ts", TESTS_DIR)
            try:
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write(typescript_script)
                print(f"Test script saved to {test_file_path}")
            except IOError as e:
                print(f"Error saving test script: {e}")
        else:
            print("No test script found in the agent's response.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python self_heal.py <pr_description_path>")
        sys.exit(1)
    main(sys.argv[1])
    
# Sample running command: python self_heal.py path/to/pr_description.txt