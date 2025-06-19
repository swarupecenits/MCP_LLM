import { test, expect } from '@playwright/test';

test('azure_ai_navigation_test', async ({ page }) => {
  // Step 1: Navigate to Azure AI Foundry Overview page
  await page.goto('https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47', { waitUntil: 'networkidle' });
  await expect(page).toHaveTitle(/Azure AI Foundry/);

  // Step 2: Click on 'Model catalog' navigation link
  await page.getByRole('link', { name: 'Model catalog' }).click();
  await page.waitForURL(/resource\/models/, { waitUntil: 'networkidle' });
  await expect(page).toHaveTitle(/Model catalog - Azure AI Foundry/);

  // Step 3: Search for 'Azure Speech' in the search box
  const searchBox = page.getByRole('searchbox', { name: 'Search' });
  await searchBox.fill('Azure Speech');
  await searchBox.press('Enter');
  await page.waitForTimeout(5000); // Wait for search results to load

  // Step 4: Verify visibility of 'Azure AI Speech'
  const azureSpeechModel = page.getByRole('link', { name: /Azure-AI-Speech/ });
  await expect(azureSpeechModel).toBeVisible({ timeout: 10000 });

  // Step 5: Close the browser
  await page.close();
});