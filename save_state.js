const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false }); // headless: false so you can log in manually
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to the login page
  await page.goto('https://ai.azure.com');

  console.log("Please log in manually in the opened browser window...");

  // Wait for user to complete login (adjust selector as needed)
  await page.waitForTimeout(60000); // Wait 60 seconds for manual login

  // Save authenticated session
  await context.storageState({ path: 'auth/storageState.json' });
  console.log("✅ Auth state saved to auth/storageState.json");

  await browser.close();
})();
