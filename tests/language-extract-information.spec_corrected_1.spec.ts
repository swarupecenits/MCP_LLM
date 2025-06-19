import { test, expect } from "@playwright/test";
import path from "path";
import { chromium } from "playwright";

// This test navigates to the Azure AI Foundry portal, goes to Playgrounds, opens the Language Playground, clicks Extract Information, and checks for the cards text heading.
test("Navigate to Language Playground and check Extract Information cards heading", async () => {
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });

  const page = await context.newPage();

  // 1. Go to the portal (assumes already logged in)
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
  );

  // 2. Click on Playgrounds in the sidebar
  await page.getByRole("link", { name: "Playgrounds" }).click();

  // 3. Click on 'Try the Language Playground'
  await page.getByRole("button", { name: "Try the Language playground" }).click();

  // 4. Click on Extract Information
  await page.getByRole("button", { name: "Extract Information" }).click();

  // 5. Check for the cards text heading visible (e.g., "Extract health information")
  await expect(page.getByText("Extract health information")).toBeVisible();

  // 6. Close the browser
  await context.close();
});
