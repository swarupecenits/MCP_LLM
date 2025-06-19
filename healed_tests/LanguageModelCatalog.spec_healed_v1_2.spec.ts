import { test } from "@playwright/test";
import { testConfig } from "../../../core/constants";
import { Owner, Tags } from "../../../core/Tags";
import { waitFor } from "../../../core/utils";
import { LanguageModelCatalogPage } from "../pages/LanguageModelCatalogPage";
import { LanguagePlaygroundPage } from "../pages/LanguagePlaygroundPage";

test.describe(`${Owner.Language} - language model catalog tryout specs`, () => {
  let languageModelCatalogPage: LanguageModelCatalogPage;
  let languagePlaygroundPage: LanguagePlaygroundPage;

  test.beforeEach(async ({ page }) => {
    languageModelCatalogPage = new LanguageModelCatalogPage(page, testConfig.staticProject);
    test.slow();
    await languageModelCatalogPage.goto();
    await languageModelCatalogPage.isVisible();
  });

  test("Try it out tab is working", { tag: Tags.Smoke }, async ({ page }) => {
    await languageModelCatalogPage.tryItOutTab();
  });

  test("API code tab is working", { tag: Tags.Smoke }, async ({ page }) => {
    await languageModelCatalogPage.apiCodeTab();
  });

  test("Use service button is available", { tag: Tags.Smoke }, async ({ page }) => {
    await languageModelCatalogPage.useServiceButtonAvailable();
  });

  test("Go to playground button is working", { tag: Tags.Smoke }, async ({ page }) => {
    languagePlaygroundPage = new LanguagePlaygroundPage(page);
    await languageModelCatalogPage.tryItOutTab();
    await languageModelCatalogPage.goToPlaygroundButton();
    await waitFor(5000);
    await languagePlaygroundPage.isVisible();
  });
});

// Updated LanguageModelCatalogPage class
export class LanguageModelCatalogPage {
  private page;
  private project;

  constructor(page, project) {
    this.page = page;
    this.project = project;
  }

  async goto() {
    const baseUrl = testConfig.baseUrl; // Ensure baseUrl is defined in testConfig
    const relativePath = `/explore/models/aiservices/Azure-AI-Language/version/1/registry/azureml-cogsvc?auth=local&tid=72f988bf-86f1-41af-91ab-2d7cd011db47&wsid=${this.project}`;
    const fullUrl = `${baseUrl}${relativePath}`;
    await this.page.goto(fullUrl, { waitUntil: "load" });
  }

  async isVisible() {
    await this.page.waitForSelector("[data-testid='language-model-catalog']", { timeout: 5000 });
  }

  async tryItOutTab() {
    await this.page.click("[data-testid='try-it-out-tab']");
  }

  async apiCodeTab() {
    await this.page.click("[data-testid='api-code-tab']");
  }

  async useServiceButtonAvailable() {
    await this.page.waitForSelector("[data-testid='use-service-button']", { timeout: 5000 });
  }

  async goToPlaygroundButton() {
    await this.page.click("[data-testid='go-to-playground-button']");
  }
}