import asyncio
import os
import re
import sys
import json
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import SecretStr

async def self_heal_playwright_script(failing_script_path: str, error_json_path: str) -> str:
    # Load environment variables
    load_dotenv()

    try:
        client = MCPClient.from_config_file("playwright_mcp.json")
    except Exception as e:
        print(f"❌ MCP client config error: {e}")
        return ""

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
        print(f"❌ LLM initialization failed: {e}")
        return ""

    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # Load input files
    try:
        with open(failing_script_path, "r", encoding="utf-8") as f:
            failing_script = f.read()
        with open(error_json_path, "r", encoding="utf-8") as f:
            error_json = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load input files: {e}")
        return ""

    # System prompt for healing
    healing_prompt = f"""
You are an expert AI test engineer integrated with a Playwright MCP server, capable of executing browser automation and DOM inspection tasks in real time.

You are given:
- A failing Playwright test script.
- An `error.json` file that includes details about the failure (e.g., selector not found, timeout, etc.).
- Access to the current DOM of the application via the MCP server.

Your task is to:
1. Analyze the failing test script and `error.json` to determine the root cause.
2. Identify flaky or broken selectors and determine their correct replacements by inspecting the live DOM via the Playwright MCP server.
3. Heal the failing Playwright script by modifying only the broken parts — preserve working logic.
4. Output the **self-healed Playwright test script**.
5. Include a summary section at the top that:
   - Describes the cause of failure.
   - Describes the fix applied (e.g., selector replaced, wait added).
   - Mentions the suggested long-term fix if applicable (e.g., use a stable attribute or test ID).

You must:
- Use selectors that are resilient and descriptive (`data-testid`, stable classes, etc.).
- Log any ambiguity or uncertainty clearly in the summary.
- Test the new script on the page (via DOM query) before finalizing it.
- Output only valid Playwright script using `@playwright/test`.

Format:

### 🧩 Healing Summary
- **Failure Cause:** <briefly explain why the original script failed>
- **Fix Applied:** <what was changed and why>
- **Suggested Fix:** <what devs can change to make the test more stable>

### ✅ Healed Test Script
```ts
<fixed playwright script here>
"""


    # Construct final prompt
    final_prompt = f"{healing_prompt}\n\n---\n\nFailing Test Script:\n```ts\n{failing_script}\n```\n\nError JSON:\n```json\n{json.dumps(error_json, indent=2)}\n```"

    try:
        response = await agent.run(final_prompt, max_steps=30)
        return response
    except Exception as e:
        print(f"❌ Error during self-healing process: {e}")
        return ""
async def main():
    if len(sys.argv) < 3:
        print("Usage: python agent_v3.py <failing_script.ts> <error.json>")
    return
    script_path = sys.argv[1]
    error_path = sys.argv[2]

    print(f"🛠 Healing script: {script_path}\n🔍 Using error data: {error_path}")

    healed_result = await self_heal_playwright_script(script_path, error_path)

    if healed_result:
        print("\n✅ Self-healed Playwright Script:\n")
        print(healed_result)
    else:
        print("\n❌ Healing failed.")
        
if __name__ == "__main__":
    asyncio.run(main())