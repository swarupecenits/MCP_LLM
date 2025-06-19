import { test, expect } from '@playwright/test';

test('Navigate and search for Azure Speech in Model Catalogue', async ({ page }) => {
  // Step 1: Navigate to the Azure AI Foundry homepage
  await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle' });
  await expect(page).toHaveTitle(/Azure AI Foundry/);

  // Step 2: Navigate to the Model Catalogue
  await page.getByRole('link', { name: 'Browse Foundry Models' }).click();
  await expect(page).toHaveURL(/catalog/);
  await expect(page).toHaveTitle(/AI Model Catalog | Microsoft Foundry Models/);

  // Step 3: Attempt to search for "Azure Speech"
  try {
    const searchInput = await page.locator('input[placeholder="Search"]');
    await searchInput.fill('Azure Speech');
    await searchInput.press('Enter');
  } catch (error) {
    console.error('Search input field not found or not interactable:', error);
  }

  // Step 4: Check if "Azure AI Speech" is visible
  const isSpeechVisible = await page.locator('text=Azure AI Speech').isVisible({ timeout: 10000 });
  console.log('Azure AI Speech visibility:', isSpeechVisible);

  // Step 5: Close the browser
  await page.close();
});