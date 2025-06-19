import { test, expect, chromium } from "@playwright/test";
import path from "path";

test("Navigate to Model Catalogue and search for Azure Speech", async () => {
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });

  const page = await context.newPage();

  // Navigate to the portal (already logged in)
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
  );

  // Click on "Model catalog" in the navigation sidebar
  await page.getByRole("link", { name: "Model catalog" }).click();

  // Type "Azure Speech" in the search bar and submit
  const searchBox = await page.getByRole("searchbox", { name: "Search" });
  await searchBox.fill("Azure Speech");
  await searchBox.press("Enter");

  // Optionally, check that results are shown (can be extended)
  await expect(page).toHaveURL(/.*models.*/);

  // Close the browser
  await context.close();
});
