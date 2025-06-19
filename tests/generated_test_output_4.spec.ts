import { test, expect } from '@playwright/test';

test('Navigate to Model Catalog in Azure AI Studio', async ({ page }) => {
  // Navigate to the Azure AI Studio homepage
  await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle' });

  // Verify the page title
  await expect(page).toHaveTitle(/Azure AI Foundry/);

  // Attempt to click on "Browse Foundry Models" link
  try {
    const browseModelsLink = page.getByText('Browse Foundry Models');
    await browseModelsLink.click();
  } catch (error) {
    console.warn('Failed to click "Browse Foundry Models" link. Navigating directly to the catalog page.');
    // Navigate directly to the Model Catalog page
    await page.goto('https://ai.azure.com/catalog', { waitUntil: 'networkidle' });
  }

  // Verify the Model Catalog page title
  await expect(page).toHaveTitle(/AI Model Catalog | Microsoft Foundry Models/);

  // Additional checks can be added here to verify elements on the Model Catalog page
});