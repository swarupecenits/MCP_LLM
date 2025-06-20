import { test, expect, chromium } from "@playwright/test";
import path from "path";


// Grader schema JSON to input
const graderSchema = `{"name":"grader-TYpcgoZgbhDW","type":"multi","graders":{"donors":{"name":"donors","type":"string_check","input":"{{item.reference_answer.donors}}","operation":"eq","reference":"{{sample.output_json.donors}}"},"acceptors":{"name":"acceptors","type":"string_check","input":"{{item.reference_answer.acceptors}}","operation":"eq","reference":"{{sample.output_json.acceptors}}"}},"calculate_output":"0.5 * donors + 0.5 *acceptors"}`;

test("Fine-tune Model E2E (o4-mini)", async () => {
  // Use persistent Chrome profile
  const userDataDir = path.resolve("C:/Users/t-schanda/AppData/Local/Google/Chrome/User Data/Profile 1");
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    args: ["--start-maximized"],
  });
  const page = await context.newPage();

  // Step 1: Navigate to the URL
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-pritam-fdp-1/providers/Microsoft.CognitiveServices/accounts/pritam-fdp-1-resource/projects/pritam-fdp-1&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
    { timeout: 60000 },
  );

  // Step 2: Go to Fine Tuning
  await page.getByRole("link", { name: "Fine-tuning" }).click({ timeout: 20000 });

  // Step 3: Click on "Fine-tune Model"
  await page.getByRole("button", { name: "Fine-tune model" }).click({ timeout: 20000 });

  // Step 4: Select o4-mini from Base Models
  await page.getByRole("radio", { name: /o4-mini/i }).click({ timeout: 20000 });
  await page.getByRole("button", { name: "Next", exact: true }).click({ timeout: 20000 });

  // Step 5: Add training data
  await page.getByRole("button", { name: "Add training data" }).click({ timeout: 20000 });
  await page.getByRole('combobox', { name: 'Select or search by name' }).click();
  await page.getByRole('option', { name: /train_500.jsonl$/ }).first().click();
  await page.getByRole("button", { name: "Apply" }).click({ timeout: 20000 });

  // Step 6: Add validation data
  await page.getByRole("button", { name: "Add validation data" }).click({ timeout: 20000 });
  await page.getByRole('combobox', { name: 'Select or search by name' }).click();
  await page.getByRole('option', { name: /validation_data_2025-05-20.jsonl$/ }).first().click();
  await page.getByRole("button", { name: "Apply" }).click({ timeout: 20000 });

  // Step 7: Enter grader schema JSON in Monaco editor (workaround)
  console.log('Before Monaco editor input');
  const monaco = page.locator(".monaco-editor textarea").first();
  await page.evaluate((text) => navigator.clipboard.writeText(text), graderSchema);
  await monaco.focus();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  await page.keyboard.press('Control+V');
  console.log('After Monaco editor input');

  // Step 8: Click on submit button
  await page.getByRole("button", { name: "Submit" }).click({ timeout: 20000 });

  // Step 9: Wait for model name to be visible (success criteria)
  await expect(page.getByText(/^o4-mini-/).first()).toBeVisible({ timeout: 60000 });

  await context.close();
}, { timeout: 90000 }); // Set test timeout to 90 seconds
