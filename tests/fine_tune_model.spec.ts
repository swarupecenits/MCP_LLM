import { test, expect, chromium } from '@playwright/test';
import path from 'path';

test('Fine-tune Model E2E', async () => {
  // Use persistent Chrome profile
  const userDataDir = path.resolve('C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1');
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    args: ['--start-maximized'],
  });
  const page = await context.newPage();

  // Step 1: Navigate to the URL
  await page.goto('https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj&tid=72f988bf-86f1-41af-91ab-2d7cd011db47', { timeout: 30000 });

  // Step 2: Go to Fine Tuning
  await page.getByRole('link', { name: 'Fine-tuning' }).click();

  // Step 3: Click on "Fine-tune Model"
  await page.getByRole('button', { name: 'Fine-tune model' }).click();

  // Step 4: Select gpt-4.1 from Base Models
  await page.getByRole('radio', { name: /gpt-4.1 Chat completion/ }).click();
  await page.getByRole('button', { name: 'Next', exact: true }).click();

  // Step 5: Click on Add Training data
  await page.getByRole('button', { name: 'Add training data' }).click();

  // Step 6: Select dropdown on Select data and pick any json file
  await page.getByRole('combobox', { name: 'Select or search by name' }).click();
  await page.getByRole('option', { name: /.jsonl$/ }).first().click();
  await page.getByRole('button', { name: 'Apply' }).click();

  // Step 7: Configure Hyperparameters
  // Batch size
  const batchSizeCheckbox = page.locator('input[type="checkbox"]').nth(0);
  await batchSizeCheckbox.check({ force: true });
  const batchSizeSlider = page.getByRole('slider', { name: 'Batch size' }).locator('span').first();
  await batchSizeSlider.click({ force: true });
  // Set Batch size value to 8
  const batchSizeInput = await batchSizeSlider.evaluateHandle((el) => {
    const slider = el.closest('[role="slider"]');
    if (!slider) return null;
    const input = slider.querySelector('input[type="range"]');
    return input ? input : null;
  });
  await batchSizeInput.evaluate((input: HTMLInputElement | null) => {
    if (input) {
      input.value = '8';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  // Learning rate multiplier
  const lrCheckbox = page.locator('input[type="checkbox"]').nth(1);
  await lrCheckbox.check({ force: true });
  const lrSlider = page.getByRole('slider', { name: 'Learning rate multiplier' }).locator('span').first();
  await lrSlider.click({ force: true });
  // Set Learning rate multiplier to 0.2
  const lrInput = await lrSlider.evaluateHandle((el) => {
    const slider = el.closest('[role="slider"]');
    if (!slider) return null;
    const input = slider.querySelector('input[type="range"]');
    return input ? input : null;
  });
  await lrInput.evaluate((input: HTMLInputElement | null) => {
    if (input) {
      input.value = '0.2';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  // Number of epochs
  const epochsCheckbox = page.locator('input[type="checkbox"]').nth(2);
  await epochsCheckbox.check({ force: true });
  const epochsSlider = page.getByRole('slider', { name: 'Number of epochs' }).locator('span').first();
  await epochsSlider.click({ force: true });
  // Set Number of epochs to 4
  const epochsInput = await epochsSlider.evaluateHandle((el) => {
    const slider = el.closest('[role="slider"]');
    if (!slider) return null;
    const input = slider.querySelector('input[type="range"]');
    return input ? input : null;
  });
  await epochsInput.evaluate((input: HTMLInputElement | null) => {
    if (input) {
      input.value = '4';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  // Step 8: Click on submit button
  await page.getByRole('button', { name: 'Submit' }).click();

  // Step 9: Wait for model name to be visible (success criteria)
  const modelName = await page.getByText(/gpt-4.1/i).first();
  await expect(modelName).toBeVisible({ timeout: 30000 });

  await context.close();
});
