import { expect, type Locator, type Page } from "@playwright/test";
import { BasePage } from "../../../core/BasePage";
import { timeouts } from "../../../core/constants";
import { step } from "../../../core/decorators";
import { TestData } from "../../../core/TestData";

export class FineTuneModelFlowPage extends BasePage {
  public page: Page;
  private readonly baseUrl = "https://ai.azure.com/foundryProject/overview";
  private readonly wsid =
    "/subscriptions/696debc0-8b66-4d84-87b1-39f43917d76c/resourceGroups/rg-t-schanda-8629/providers/Microsoft.CognitiveServices/accounts/playwright-pj-resource/projects/playwright_pj";
  private readonly tid = "72f988bf-86f1-41af-91ab-2d7cd011db47";

  constructor(page: Page) {
    super(page);
    this.page = page;
  }

  @step()
  public async navigateToFineTuningPage(): Promise<void> {
    await this.page.goto(`${this.baseUrl}?wsid=${this.wsid}&tid=${this.tid}`, {
      waitUntil: "networkidle",
      timeout: timeouts.slowExpect,
    });

    // Navigate to Fine Tuning section
    await this.page.getByRole("link", { name: "Fine-tuning" }).click();

    // Wait for the Fine Tuning page to load
    await expect(this.page.getByTestId("pageTitle")).toBeVisible({
      timeout: timeouts.search,
    });
  }

  @step()
  public async startFineTuneModelFlow(): Promise<void> {
    // Click on Fine-tune Model button
    await this.page.getByRole("button", { name: "Fine-tune model" }).click();

    // Wait for model picker to be visible
    await this.page.locator("#model-picker-entity-list").waitFor({
      state: "visible",
      timeout: timeouts.search,
    });
  }

  @step()
  public async selectGPT41Model(): Promise<void> {
    // Select GPT-4.1 model
    const modelLocator = this.page.getByText("gpt-4.1", { exact: true });
    await modelLocator.first().waitFor({
      state: "visible",
      timeout: timeouts.search,
    });
    await modelLocator.first().click();

    // Click Next button
    await this.page.getByRole("button", { name: "Next", exact: true }).click();

    // Wait for fine-tune wizard to be visible
    await expect(this.page.getByTestId("finetuneWizard")).toBeVisible({
      timeout: timeouts.slowExpect,
    });
  }

  @step()
  public async addTrainingData(fileName: string): Promise<void> {
    // Click Add Training Data button
    await this.page.getByRole("button", { name: "Add Training data" }).click();

    // Click on Select data dropdown
    await this.page.getByPlaceholder("Select a data source").click();

    // Wait for dropdown options to be visible
    await this.page.getByRole("listbox").waitFor({
      state: "visible",
      timeout: timeouts.search,
    });

    // Select the first available JSON file
    await this.page.getByRole("option").first().click();

    // Click Apply button
    await this.page.getByRole("button", { name: "Apply" }).click();

    // Wait for the data to be applied
    await expect(this.page.getByText("Training data added successfully")).toBeVisible({
      timeout: timeouts.slowExpect,
    });
  }

  @step()
  public async submitAndWaitForModel(): Promise<void> {
    // Click Submit button
    await this.page.getByRole("button", { name: "Submit" }).click();

    // Wait for model creation to start and name to appear
    await expect(this.page.getByTestId("fineTuneModelList")).toBeVisible({
      timeout: timeouts.slowExpect,
    });

    // Wait for the model name to appear in the list
    await expect(this.page.getByRole("row").first()).toBeVisible({
      timeout: timeouts.slowExpect,
    });
  }
}
