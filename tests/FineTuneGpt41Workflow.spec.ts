import { test } from "@playwright/test";
import { Owner, Tags } from "../../../core/Tags";
import { FinetunePage } from "../pages/FinetuneNewUIPage";

const allAOAIResourceConnections = ["singh-m99ulasi-northcentralus_aoai"];
const chatTrainingDataAssetName = "messages_jsonl_2025-05-13_090600_UTC";

// This test follows the manual workflow logic from the previous fine_tune_gpt41.spec.ts

test.describe(`${Owner.Training} - Fine-tune GPT-4.1 workflow`, () => {
  let fineTunePage: FinetunePage;

  test.beforeEach(async ({ page }) => {
    fineTunePage = new FinetunePage(page);
    await fineTunePage.navigateToFinetunePage({});
  });

  test(
    "should complete the fine-tune GPT-4.1 model workflow successfully",
    { tag: [Tags.StaticResource, Tags.Smoke] },
    async () => {
      // 1. Ensure page loaded
      await fineTunePage.isFinetunePageLoadedSuccessfully();
      // 2. Open wizard and select model
      await fineTunePage.selectModelAndOpenFinetuneWizard();
      // 3. Fill basic settings (default method)
      await fineTunePage.testBasicSettingSpecs(allAOAIResourceConnections);
      // 4. Add training data
      await fineTunePage.testTrainingDataSpecs(chatTrainingDataAssetName);
      // 5. Submit model
      await fineTunePage.submitModel();
      // 6. Wait for model name to be visible (handled in submitModel or can be added here)
    },
  );
});
