import { test, expect, chromium } from "@playwright/test";
import path from "path";

test("Azure AI Foundry Language Playground navigation", async () => {
  test.setTimeout(120000); // Increase timeout to 2 minutes for slow UI
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });
  const page = await context.newPage();

  // Step 1: Go to the portal overview page
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
  );
  await page.waitForSelector('[data-testid="playgrounds-link"]', { state: "visible", timeout: 30000 });

  // Step 2: Go to Playgrounds
  await page.locator('[data-testid="playgrounds-link"]').click();
  await page.waitForSelector('[data-testid="language-playground-button"]', { state: "visible", timeout: 30000 });

  // Step 3: Go to Language Playground
  await page.locator('[data-testid="language-playground-button"]').click();
  await page.waitForSelector('[data-testid="all-button"]', { state: "visible", timeout: 30000 });

  // Step 4: Navigate through the panel buttons like a human
  await page.locator('[data-testid="all-button"]').click();
  await page.locator('[data-testid="extract-information-button"]').click();
  await page.locator('[data-testid="summarize-information-button"]').click();
  await page.locator('[data-testid="classify-text-button"]').click();
  await page.locator('[data-testid="fine-tune-models-button"]').click();

  // Step 5: Check cards in the panel (sample: click on "Extract key phrases")
  await page.locator('[data-testid="extract-key-phrases-card"]').click();
  await expect(page.locator('[data-testid="extract-key-phrases-card"]')).toBeVisible();

  // Step 6: Return to All and check another card
  await page.locator('[data-testid="all-button"]').click();
  await page.locator('[data-testid="analyze-sentiment-card"]').click();
  await expect(page.locator('[data-testid="analyze-sentiment-card"]')).toBeVisible();

  // Step 7: Close browser
  await context.close();
});