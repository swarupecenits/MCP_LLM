import { test } from "@playwright/test";
import { scopes } from "../../../core/constants";
import { Owner, Tags } from "../../../core/Tags";
import { FinetunePage } from "../pages/FinetuneNewUIPage";

const allAOAIResourceConnections = ["singh-m99ulasi-northcentralus_aoai"];
const chatTrainingDataAssetName = "messages_jsonl_2025-05-13_090600_UTC";

[{ name: scopes.resource }].forEach(({ name }: { name: string }) => {
  test.describe(`${Owner.Training} - fine tuning page specs for ${name} scope`, () => {
    let fineTunePage: FinetunePage;

    test.beforeEach(async ({ page }) => {
      fineTunePage = new FinetunePage(page);
      await fineTunePage.navigateToFinetunePage({});
    });

    test(
      "test if fine-tuning page can be loaded successfully",
      { tag: [Tags.StaticResource, Tags.Smoke] },
      async () => {
        await fineTunePage.isFinetunePageLoadedSuccessfully();
      },
    );

    test(
      "test gpt-4.1 finetuning in project scope",
      { tag: [Tags.StaticResource] },
      async ({ page }) => {
        test.slow();
        await fineTunePage.isFinetunePageLoadedSuccessfully();
        await fineTunePage.selectModelAndOpenFinetuneWizard();
        await fineTunePage.testBasicSettingSpecs(allAOAIResourceConnections);
        await fineTunePage.testTrainingDataSpecs(chatTrainingDataAssetName);

        // --- Configure Hyperparameters section ---
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
        // --- End Configure Hyperparameters section ---

        await fineTunePage.submitModel();
        await fineTunePage.cancelModel();
        await fineTunePage.deleteModel();
      },
    );
  });
});
