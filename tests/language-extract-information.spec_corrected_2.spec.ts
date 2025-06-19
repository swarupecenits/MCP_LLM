import { test, expect, chromium } from "@playwright/test";
import path from "path";

test("Navigate to Language Playground and check Extract Information cards heading", async () => {
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");

  // Launch browser with persistent context
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });

  const page = await context.newPage();

  try {
    // Step 1: Navigate to the Azure AI Foundry portal
    await page.goto(
      "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
      { waitUntil: "domcontentloaded", timeout: 60000 }
    );

    // Wait for the page to fully load
    await page.waitForLoadState("networkidle");
    await page.waitForSelector("text=Loading user settings…", { state: "detached", timeout: 30000 });

    // Step 2: Click on "Playgrounds" in the sidebar
    const playgroundsLink = await page.waitForSelector('a[role="link"][name="Playgrounds"]', { timeout: 30000 });
    await playgroundsLink.click();

    // Step 3: Click on "Try the Language Playground"
    const languagePlaygroundButton = await page.waitForSelector('button[role="button"][name="Try the Language playground"]', { timeout: 30000 });
    await languagePlaygroundButton.click();

    // Step 4: Click on "Extract Information"
    const extractInformationButton = await page.waitForSelector('button[role="button"][name="Extract Information"]', { timeout: 30000 });
    await extractInformationButton.click();

    // Step 5: Check for the "Extract health information" heading
    const extractHealthHeading = await page.waitForSelector('label[role="label"][name="Extract health information"]', { timeout: 30000 });
    await expect(extractHealthHeading).toBeVisible();

  } catch (error) {
    console.error("Test failed due to error:", error);
    throw error; // Rethrow the error to mark the test as failed
  } finally {
    // Step 6: Close the browser
    await context.close();
  }
});