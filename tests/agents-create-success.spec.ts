import { test, expect, chromium } from "@playwright/test";
import path from "path";

test("Navigate to portal, go to Agents, refresh, create new agent and check success", async () => {
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });

  const page = await context.newPage();

  // Step 1: Navigate to the portal (already logged in)
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
  );

  // Step 2: Go to Agents
  await page.getByRole("link", { name: "Agents", exact: true }).click();
  await page.getByRole("button", { name: "Refresh" }).waitFor({ state: "visible" });

  // Step 3: Click Refresh
  await page.getByRole("button", { name: "Refresh" }).click();

  // Step 4: Click on 'New agent'
  await page.getByRole("button", { name: "New agent" }).click();

  // Step 5: Check for the 'Success' message
  const successLocator = page.getByRole("alert");
  await expect(successLocator).toContainText("Success");

  // Step 6: Close the browser
  await context.close();
});
