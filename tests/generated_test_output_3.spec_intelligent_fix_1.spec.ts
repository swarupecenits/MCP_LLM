import { test, expect } from '@playwright/test';

test('Azure AI Speech Search Test', async ({ page }) => {
  try {
    // Step 1: Navigate to Azure AI Foundry
    await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle' });
    console.log('Navigated to Azure AI Foundry');

    // Step 2: Click on 'Browse Foundry Models' link
    const browseModelsLink = page.locator('text=Browse Foundry Models'); // Fallback to text-based locator
    await browseModelsLink.waitFor({ state: 'visible', timeout: 15000 });
    await browseModelsLink.click();
    console.log('Clicked on "Browse Foundry Models" link');

    // Step 3: Click on 'Go to full model catalog' link
    const fullModelCatalogLink = page.locator('text=Go to full model catalog'); // Using text-based locator
    await fullModelCatalogLink.waitFor({ state: 'visible', timeout: 15000 });
    await fullModelCatalogLink.click();
    console.log('Clicked on "Go to full model catalog" link');

    // Step 4: Search for 'Azure Speech' in the search box
    const searchBox = page.locator('[data-testid="search-box"]'); // Using data-testid for reliability
    await searchBox.waitFor({ state: 'visible', timeout: 15000 });
    await searchBox.fill('Azure Speech');
    await searchBox.press('Enter');
    console.log('Searched for "Azure Speech"');

    // Step 5: Verify if 'Azure AI Speech' is visible
    const azureSpeechModel = page.locator('a:has-text("Azure-AI-Speech")'); // Using CSS selector with partial text match
    await azureSpeechModel.waitFor({ state: 'visible', timeout: 15000 });
    console.log('Verified "Azure AI Speech" is visible');

  } catch (error) {
    console.error('Test failed:', error);
    throw error; // Re-throw the error to fail the test
  } finally {
    // Step 6: Close the browser
    await page.close();
    console.log('Browser closed');
  }
});