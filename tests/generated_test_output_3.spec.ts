import { test, expect } from '@playwright/test';

test('Azure AI Speech Search Test', async ({ page }) => {
  // Step 1: Navigate to Azure AI Foundry
  await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle' });

  // Step 2: Click on 'Browse Foundry Models' link
  const browseModelsLink = page.getByRole('link', { name: 'Browse Foundry Models' });
  await expect(browseModelsLink).toBeVisible({ timeout: 10000 });
  await browseModelsLink.click();

  // Step 3: Click on 'Go to full model catalog' link
  const fullModelCatalogLink = page.getByRole('link', { name: 'Go to full model catalog' });
  await expect(fullModelCatalogLink).toBeVisible({ timeout: 10000 });
  await fullModelCatalogLink.click();

  // Step 4: Search for 'Azure Speech' in the search box
  const searchBox = page.getByRole('searchbox', { name: 'Search' });
  await expect(searchBox).toBeVisible({ timeout: 10000 });
  await searchBox.fill('Azure Speech');
  await searchBox.press('Enter');

  // Step 5: Verify if 'Azure AI Speech' is visible
  const azureSpeechModel = page.getByRole('link', { name: /Azure-AI-Speech/ });
  await expect(azureSpeechModel).toBeVisible({ timeout: 10000 });

  // Step 6: Close the browser
  await page.close();
});