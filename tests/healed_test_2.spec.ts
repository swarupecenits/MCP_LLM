import { test, expect } from "@playwright/test";
import path from "path";
import { chromium } from "playwright";

test("Navigate to Language Playground and check Extract Information cards heading", async () => {
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");

  // Launch a persistent browser context
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });

  const page = await context.newPage();

  try {
    // 1. Navigate to the Azure AI Foundry portal
    await page.goto(
      "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
      { waitUntil: "domcontentloaded", timeout: 15000 }
    );

    // 2. Click on "Playgrounds" in the sidebar
    const playgroundsLink = page.getByRole("link", { name: "Playgrounds" });
    await expect(playgroundsLink).toBeVisible({ timeout: 10000 });
    await playgroundsLink.click();

    // 3. Click on "Try the Language Playground"
    const languagePlaygroundButton = page.getByRole("button", { name: "Try the Language playground" });
    await expect(languagePlaygroundButton).toBeVisible({ timeout: 10000 });
    await languagePlaygroundButton.click();

    // 4. Click on "Extract Information"
    const extractInformationButton = page.getByRole("button", { name: "Extract Information" });
    await expect(extractInformationButton).toBeVisible({ timeout: 10000 });
    await extractInformationButton.click();

    // 5. Check for the cards text heading visible (e.g., "Extract health information")
    const extractHealthInfoHeading = page.locator('[aria-label="Extract health information"]');
    await expect(extractHealthInfoHeading).toBeVisible({ timeout: 15000 });

    // 6. Handle "All" buttons with strict locators
    const resourcesButton = page.getByTestId("resourcesButton");
    await expect(resourcesButton).toBeVisible({ timeout: 10000 });
    await resourcesButton.click();

    const allButton = page.getByRole("button", { name: "All", exact: true });
    await expect(allButton).toBeVisible({ timeout: 10000 });
    await allButton.click();

  } catch (error) {
    console.error("Test failed with error:", error);
    throw error; // Re-throw the error to fail the test
  } finally {
    // 7. Close the browser
    await context.close();
  }
});