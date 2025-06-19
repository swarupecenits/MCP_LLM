import { test, expect } from '@playwright/test';

test('Navigate to example.com and verify page title and visibility of key element', async ({ page }) => {
  // Navigate to the URL
  await page.goto('https://example.com', { waitUntil: 'networkidle', timeout: 10000 });

  // Verify the page title
  await expect(page).toHaveTitle(/Example Domain/);

  // Check for the visibility of the main heading
  const heading = page.locator('h1');
  await expect(heading).toBeVisible({ timeout: 15000 });

  // Optionally check for the visibility of the paragraph
  const paragraph = page.locator('p');
  await expect(paragraph).toBeVisible({ timeout: 15000 });
});