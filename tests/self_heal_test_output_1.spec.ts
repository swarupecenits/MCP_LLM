import { test, expect } from '@playwright/test';

test('Navigate to Azure AI Foundry Language Playground and verify accessibility', async ({ page }) => {
  // Step 1: Navigate to the Azure AI Foundry Language Playground
  await page.goto('https://azure.microsoft.com/en-us/products/ai-services/', { waitUntil: 'networkidle', timeout: 10000 });

  // Step 2: Verify the page title contains "AI Services"
  await expect(page).toHaveTitle(/AI Services/, { timeout: 15000 });

  // Step 3: Check for optional popups or overlays (e.g., consent dialogs)
  const consentPopup = await page.locator('text=Accept Cookies').first();
  if (await consentPopup.isVisible()) {
    await consentPopup.click();
  }

  // Step 4: Locate and click on the "Language Playground" link
  const languagePlaygroundLink = await page.getByRole('link', { name: 'Language Playground' });
  await expect(languagePlaygroundLink).toBeVisible({ timeout: 15000 });
  await languagePlaygroundLink.click();

  // Step 5: Wait for the Language Playground page to load
  await page.waitForURL('https://azure.microsoft.com/en-us/products/ai-services/language-playground/', { waitUntil: 'networkidle', timeout: 10000 });

  // Step 6: Verify the Language Playground page is accessible
  const playgroundHeader = await page.getByRole('heading', { name: 'Language Playground' });
  await expect(playgroundHeader).toBeVisible({ timeout: 15000 });

  // Step 7: Ensure the page is stable and ready for interaction
  await page.waitForLoadState('networkidle');

  // Final Assertion: Confirm the Language Playground is accessible
  console.log('Language Playground is accessible and ready for use.');
});