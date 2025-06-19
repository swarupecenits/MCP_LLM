import { test, expect } from '@playwright/test';

test('Verify Azure AI Speech visibility', async ({ page }) => {
  await page.goto('https://ai.azure.com?auth=local', { waitUntil: 'networkidle', timeout: 10000 });
  await page.locator('#model-catalogue-link').click();
  await page.waitForLoadState('networkidle');
  await page.locator('#search-input').fill('Azure Speech');
  await page.locator('#search-button').click();
  await page.waitForLoadState('networkidle');
  const speechElement = page.locator('.speech-model');
  await expect(speechElement).toBeVisible({ timeout: 5000 });
});