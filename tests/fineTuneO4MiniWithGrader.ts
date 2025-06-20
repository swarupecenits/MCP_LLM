import { test, expect } from "@playwright/test";
import { timeouts } from "../../../core/constants";
import { waitFor } from "../../../core/utils";

// Grader schema JSON to input
const graderSchema = `{"name":"grader-TYpcgoZgbhDW","type":"multi","graders":{"donors":{"name":"donors","type":"string_check","input":"{{item.reference_answer.donors}}","operation":"eq","reference":"{{sample.output_json.donors}}"},"acceptors":{"name":"acceptors","type":"string_check","input":"{{item.reference_answer.acceptors}}","operation":"eq","reference":"{{sample.output_json.acceptors}}"}},"calculate_output":"0.5 * donors + 0.5 *acceptors"}`;

export async function fineTuneO4MiniWithGrader(page: import("@playwright/test").Page): Promise<void> {
  // Step 1: Navigate to the URL
  await page.goto(
    "https://ai.azure.com/foundryProject/overview?wsid=/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-pritam-fdp-1/providers/Microsoft.CognitiveServices/accounts/pritam-fdp-1-resource/projects/pritam-fdp-1&tid=72f988bf-86f1-41af-91ab-2d7cd011db47",
    { timeout: timeouts.setup },
  );

  // Step 2: Go to Fine Tuning
  await page.getByRole("link", { name: "Fine-tuning" }).click({ timeout: timeouts.slowExpect });

  // Step 3: Click on "Fine-tune Model"
  await page.getByRole("button", { name: "Fine-tune model" }).click({ timeout: timeouts.slowExpect });

  // Step 4: Select o4-mini from Base Models
  await page.getByRole("radio", { name: /o4-mini/i }).click({ timeout: timeouts.slowExpect });
  await page.getByRole("button", { name: "Next", exact: true }).click({ timeout: timeouts.slowExpect });

  // Step 5: Add training data
  await page.getByRole("button", { name: "Add training data" }).click({ timeout: timeouts.slowExpect });
  await page.getByRole("combobox", { name: "Select or search by name" }).click();
  await page.getByRole("option", { name: /train_500.jsonl$/ }).first().click();
  await page.getByRole("button", { name: "Apply" }).click({ timeout: timeouts.slowExpect });

  // Step 6: Add validation data
  await page.getByRole("button", { name: "Add validation data" }).click({ timeout: timeouts.slowExpect });
  await page.getByRole("combobox", { name: "Select or search by name" }).click();
  await page.getByRole("option", { name: /validation_data_2025-05-20.jsonl$/ }).first().click();
  await page.getByRole("button", { name: "Apply" }).click({ timeout: timeouts.slowExpect });

  // Step 7: Enter grader schema JSON in Monaco editor (workaround)
  const monaco = page.locator(".monaco-editor textarea").first();
  await page.evaluate(text => navigator.clipboard.writeText(text), graderSchema);
  await monaco.focus();
  await page.keyboard.press("Control+A");
  await page.keyboard.press("Backspace");
  await page.keyboard.press("Control+V");

  // Step 8: Click on submit button
  await page.getByRole("button", { name: "Submit" }).click({ timeout: timeouts.slowExpect });

  // Step 9: Wait for model name to be visible (success criteria)
  await expect(page.getByText(/^o4-mini-/).first()).toBeVisible({ timeout: timeouts.slowExpect });

  // Optionally, wait for a short period to ensure UI is stable
  await waitFor(2000);
}
