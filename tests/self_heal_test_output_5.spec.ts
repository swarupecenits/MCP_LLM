import { test, expect, chromium } from "@playwright/test";
import path from "path";

test("Azure AI Foundry Language Playground navigation", async () => {
  test.setTimeout(120000); // Increase timeout to 2 minutes for slow UI

  // Launch browser with persistent context
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });
  const page = await context.newPage();

  try {
    // Step 1: Navigate to the portal overview page
    await page.goto(
      "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
      { waitUntil: "networkidle", timeout: 60000 }
    );
    await expect(page.getByText("Playgrounds").first()).toBeVisible({ timeout: 30000 });

    // Step 2: Navigate to Playgrounds
    const playgroundsLink = page.getByRole("link", { name: "Playgrounds" });
    await playgroundsLink.click();
    await expect(page.getByRole("button", { name: "Try the Language playground" })).toBeVisible({ timeout: 30000 });

    // Step 3: Open the Language Playground
    const tryLanguagePlaygroundButton = page.getByRole("button", { name: "Try the Language playground" });
    await tryLanguagePlaygroundButton.click();
    await expect(page.getByRole("button", { name: "All", exact: true })).toBeVisible({ timeout: 30000 });

    // Step 4: Interact with panel buttons
    const panelButtons = [
      "All",
      "Extract Information",
      "Summarize Information",
      "Classify Text",
      "Fine-tune models",
    ];
    for (const buttonName of panelButtons) {
      const button = page.getByRole("button", { name: buttonName });
      await button.click();
      await expect(button).toBeVisible({ timeout: 15000 });
    }

    // Step 5: Verify cards in the panel
    const extractKeyPhrasesCard = page.getByText("Extract key phrases");
    await extractKeyPhrasesCard.click();
    await expect(extractKeyPhrasesCard).toBeVisible({ timeout: 15000 });

    // Step 6: Return to "All" and verify another card
    const allButton = page.getByRole("button", { name: "All", exact: true });
    await allButton.click();
    const analyzeSentimentCard = page.getByText("Analyze sentiment");
    await analyzeSentimentCard.click();
    await expect(analyzeSentimentCard).toBeVisible({ timeout: 15000 });
  } catch (error) {
    console.error("Test failed with error:", error);
    throw error; // Re-throw the error to mark the test as failed
  } finally {
    // Step 7: Close the browser
    await context.close();
  }
});