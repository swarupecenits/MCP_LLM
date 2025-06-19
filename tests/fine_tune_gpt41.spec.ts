import { test, expect, chromium } from '@playwright/test';
import path from 'path';

test('Fine-tune GPT-4.1 model workflow', async () => {
  // Use persistent Chrome profile
  const userDataDir = path.resolve('C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1');
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    args: ['--start-maximized'],
  });
  const page = await context.newPage();

  // Step 1: Navigate to the project overview
  await page.goto('https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47', { timeout: 60000 });

  // Step 2: Go to Fine Tuning
  await page.getByRole('link', { name: 'Fine-tuning' }).click();
  await expect(page.getByRole('heading', { name: /Fine-tune with your own data/i })).toBeVisible({ timeout: 30000 });

  // Step 3: Click on "Fine-tune Model"
  await page.getByRole('button', { name: 'Fine-tune model' }).click();
  // Wait for the heading in the dialog instead of dialog role
  await expect(page.getByRole('heading', { name: /Select a model to fine-tune/i })).toBeVisible({ timeout: 40000 });

  // Step 4: Select gpt-4.1 from Base Models
  await page.getByRole('radio', { name: /gpt-4.1 Chat completion/i }).click();

  // Step 5: Click on next
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Create a fine-tuned model/i })).toBeVisible({ timeout: 20000 });

  // Step 6: Click on Add Training data
  await page.getByRole('button', { name: 'Add training data' }).click();
  await expect(page.getByRole('heading', { name: /Fine-tune gpt-4.1/i })).toBeVisible({ timeout: 20000 });

  // Step 7: Select dropdown on Select data
  await page.getByRole('combobox', { name: 'Select or search by name' }).click();
  // Step 8: Select any json file (first option)
  const options = await page.locator('[role="option"]').all();
  if (options.length > 0) {
    await options[0].click();
  } else {
    throw new Error('No training data options found');
  }

  // Step 9: Click on Apply
  await page.getByRole('button', { name: 'Apply' }).click();

  // Step 10: Click on submit button
  await page.getByRole('button', { name: 'Submit' }).click();

  // Step 11: Wait till the model name gets visible in the page
  await expect(page.getByText('Model name')).toBeVisible({ timeout: 60000 });

  // Close browser
  await context.close();
});
