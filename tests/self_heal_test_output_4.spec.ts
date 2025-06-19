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

  // Step 1: Navigate to the portal overview page
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
    { waitUntil: "networkidle" }
  );
  await expect(page.getByText("Playgrounds").first()).toBeVisible({ timeout: 20000 });

  // Step 2: Navigate to Playgrounds
  await page.getByRole("link", { name: "Playgrounds" }).click();
  await expect(page.getByRole("button", { name: "Try the Language playground" })).toBeVisible({ timeout: 20000 });

  // Step 3: Open the Language Playground
  await page.getByRole("button", { name: "Try the Language playground" }).click();
  await expect(page.getByRole("button", { name: "All", exact: true })).toBeVisible({ timeout: 20000 });

  // Step 4: Interact with panel buttons
  const panelButtons = [
    "All",
    "Extract Information",
    "Summarize Information",
    "Classify Text",
    "Fine-tune models",
  ];
  for (const buttonName of panelButtons) {
    await page.getByRole("button", { name: buttonName }).click();
  }

  // Step 5: Verify cards in the panel
  await page.getByText("Extract key phrases").click();
  await expect(page.getByText("Extract key phrases")).toBeVisible();

  // Step 6: Return to "All" and verify another card
  await page.getByRole("button", { name: "All", exact: true }).click();
  await page.getByText("Analyze sentiment").click();
  await expect(page.getByText("Analyze sentiment")).toBeVisible();

  // Step 7: Close the browser
  await context.close();
});