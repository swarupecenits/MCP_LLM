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
  await page.getByRole("link", { name: "Playgrounds" }).waitFor({ state: "visible", timeout: 5000 });

  // Step 2: Go to Playgrounds
  await page.getByRole("link", { name: "Playgrounds" }).click();
  await page.getByRole("button", { name: "Try the Language playground" }).waitFor({ state: "visible" });

  // Step 3: Go to Language Playground
  await page.getByRole("button", { name: "Try the Language playground" }).click();
  await page.getByRole("button", { name: "All", exact: true }).waitFor({ state: "visible" });

  // Step 4: Navigate through the panel buttons like a human
  await page.getByRole("button", { name: "All", exact: true }).click();
  await page.getByRole("button", { name: "Extract Information" }).click();
  await page.getByRole("button", { name: "Summarize Information" }).click();
  await page.getByRole("button", { name: "Classify Text" }).click();
  await page.getByRole("button", { name: "Fine-tune models" }).click();

  await page.getByRole("button", { name: "Extract Information" }).click();
  // Step 5: Check cards in the panel (sample: click on "Extract key phrases")
  await page.getByText("Extract key phrases").click();
  await expect(page.getByText("Extract key phrases")).toBeVisible();

  // Step 7: Close browser
  await context.close();
});