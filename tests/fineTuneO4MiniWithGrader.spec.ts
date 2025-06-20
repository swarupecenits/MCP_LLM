import { test } from "@playwright/test";
import { fineTuneO4MiniWithGrader } from "../fineTuneO4MiniWithGrader";

test.describe("@Training @long-running Fine-tune Model E2E (o4-mini) with Grader", () => {
  test("should fine-tune o4-mini with grader schema and data", async ({ page }) => {
    await fineTuneO4MiniWithGrader(page);
  });
});
