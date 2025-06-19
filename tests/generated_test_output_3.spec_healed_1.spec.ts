import { test, expect } from '@playwright/test';

test('Azure AI Speech Search Test', async ({ page }) => {
  // Helper function for self-healing locators
  async function findElement(page, locators: string[]) {
    for (const locator of locators) {
      try {
        const element = eval(locator);
        await element.waitFor({ timeout: 30000, state: 'visible' });
        console.log(`Found element using: ${locator}`);
        return element;
      } catch (e) {
        console.log(`Failed locator: ${locator} - ${e.message}`);
      }
    }
    throw new Error(`All locators failed for: ${locators.join(', ')}`);
  }

  // Step 1: Navigate to Azure AI Foundry
  await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle' });

  // Step 2: Click on 'Browse Foundry Models' link
  const browseModelsLocators = [
    "page.getByRole('link', { name: 'Browse Foundry Models' })",
    "page.locator('a:has-text(\"Browse Foundry Models\")')",
    "page.getByText('Browse Foundry Models')"
  ];
  const browseModelsLink = await findElement(page, browseModelsLocators);
  await browseModelsLink.click();

  // Step 3: Click on 'Go to full model catalog' link
  const fullModelCatalogLocators = [
    "page.getByRole('link', { name: 'Go to full model catalog' })",
    "page.locator('a:has-text(\"Go to full model catalog\")')",
    "page.getByText('Go to full model catalog')"
  ];
  const fullModelCatalogLink = await findElement(page, fullModelCatalogLocators);
  await fullModelCatalogLink.click();

  // Step 4: Search for 'Azure Speech' in the search box
  const searchBoxLocators = [
    "page.getByRole('searchbox', { name: 'Search' })",
    "page.locator('input[placeholder=\"Search\"]')",
    "page.getByPlaceholder('Search')"
  ];
  const searchBox = await findElement(page, searchBoxLocators);
  await searchBox.fill('Azure Speech');
  await searchBox.press('Enter');

  // Step 5: Verify if 'Azure AI Speech' is visible
  const azureSpeechModelLocators = [
    "page.getByRole('link', { name: /Azure-AI-Speech/ })",
    "page.locator('a:has-text(\"Azure-AI-Speech\")')",
    "page.getByText(/Azure-AI-Speech/)"
  ];
  const azureSpeechModel = await findElement(page, azureSpeechModelLocators);
  await expect(azureSpeechModel).toBeVisible({ timeout: 30000 });

  // Step 6: Close the browser
  await page.close();
});