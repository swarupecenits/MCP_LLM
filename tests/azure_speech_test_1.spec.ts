import { test, expect } from '@playwright/test';

test('Navigate to Azure AI Foundry and search for Azure Speech', async ({ page }) => {
  // Navigate to the Azure AI Foundry page
  await page.goto('https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-a8b1-39f43917d76c/resourceGroups/rg-t-schanda-8629-t/providers/Microsoft.CognitiveServices.accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47', { waitUntil: 'networkidle' });

  // Verify the page title
  await expect(page).toHaveTitle(/Azure AI Foundry/);

  // Navigate to Model Catalogue
  const modelCatalogueLink = page.locator('text=Model catalog');
  await modelCatalogueLink.click();

  // Wait for the page to load
  await page.waitForURL(/models/, { timeout: 10000 });

  // Search for "Azure Speech"
  const searchInput = page.locator('input[placeholder="Search"]');
  await searchInput.fill('Azure Speech');
  await searchInput.press('Enter');

  // Verify if "Azure AI Speech" is visible
  const azureSpeechResult = page.locator('text=Azure AI Speech');
  const isVisible = await azureSpeechResult.isVisible();
  console.log(`Azure AI Speech visibility: ${isVisible}`);

  // Close the browser
  await page.close();
});