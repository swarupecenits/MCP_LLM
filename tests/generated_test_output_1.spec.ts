import { test, expect } from '@playwright/test';

test('Navigate and search for Azure Speech in Model Catalogue', async ({ page }) => {
  // Navigate to the Azure AI Foundry page
  await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle' });

  // Click on "Browse Foundry Models" to navigate to the Model Catalogue
  await page.getByRole('link', { name: 'Browse Foundry Models' }).click();

  // Verify navigation to the Model Catalogue
  await expect(page).toHaveURL('https://ai.azure.com/catalog', { timeout: 10000 });

  // Attempt to search for "Azure Speech" (assuming a search input exists)
  const searchInput = page.locator('input[placeholder="Search models"]'); // Adjust selector based on actual input field
  await expect(searchInput).toBeVisible({ timeout: 10000 });
  await searchInput.fill('Azure Speech');
  await searchInput.press('Enter');

  // Check if "Azure AI Speech" is visible
  const azureSpeechModel = page.getByText('Azure AI Speech');
  const isVisible = await azureSpeechModel.isVisible();
  console.log(`Azure AI Speech visibility: ${isVisible}`);

  // Close the browser
  await page.close();
});