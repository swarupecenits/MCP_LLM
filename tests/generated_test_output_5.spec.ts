import { test, expect } from '@playwright/test';

test('Navigate to Model Catalogue in Azure AI Studio workspace-portal', async ({ page }) => {
  // Navigate to the Azure AI Studio workspace-portal application
  await page.goto('https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47', { waitUntil: 'networkidle' });

  // Verify the page title
  await expect(page).toHaveTitle('Azure AI Foundry');

  // Wait for the "Model Catalogue" navigation element to be visible
  const modelCatalogueButton = page.locator('div').filter({ hasText: 'Loading user settings…Loading' }).nth(1);
  await expect(modelCatalogueButton).toBeVisible({ timeout: 10000 });

  // Click on the "Model Catalogue" navigation element
  await modelCatalogueButton.click();

  // Add additional assertions or actions here if needed
});