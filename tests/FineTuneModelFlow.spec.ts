import { test } from "@playwright/test";
import { scopes, timeouts } from "../../../core/constants";
import { Owner, Tags } from "../../../core/Tags";
import { FineTuneModelFlowPage } from "../pages/FineTuneModelFlow";

test.describe(`${Owner.Training} - fine tuning model flow specs`, () => {
  let fineTuneModelPage: FineTuneModelFlowPage;

  test.beforeEach(async ({ page }) => {
    fineTuneModelPage = new FineTuneModelFlowPage(page);
  });

  test(
    "should create a fine-tuned model with GPT-4.1",
    {
      tag: [Tags.StaticResource],
    },
    async () => {
      test.slow(); // Mark as slow test
      test.setTimeout(timeouts.slowTest);

      // Navigate to fine tuning page
      await fineTuneModelPage.navigateToFineTuningPage();

      // Start fine-tune model flow
      await fineTuneModelPage.startFineTuneModelFlow();

      // Select GPT-4.1 model
      await fineTuneModelPage.selectGPT41Model();

      // Add training data
      await fineTuneModelPage.addTrainingData("sample.json");

      // Submit and wait for model creation
      await fineTuneModelPage.submitAndWaitForModel();
    },
  );

  test("should load fine-tuning page successfully", { tag: [Tags.StaticResource, Tags.Smoke] }, async () => {
    await fineTuneModelPage.navigateToFineTuningPage();
  });
});
