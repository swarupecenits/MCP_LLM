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
    const baseUrl = "https://ai.azure.com";
    const relativePath = `/explore/models/aiservices/Azure-AI-Language/version/1/registry/azureml-cogsvc?auth=local&tid=72f988bf-86f1-41af-91ab-2d7cd011db47&wsid=${this.project}`;
    await this.page.goto(`${baseUrl}${relativePath}`);
  }

  async isVisible() {
    await this.page.waitForSelector("text=Language Model Catalog");
  }

  async tryItOutTab() {
    await this.page.click("text=Try it out");
  }

  async apiCodeTab() {
    await this.page.click("text=API Code");
  }

  async useServiceButtonAvailable() {
    await this.page.waitForSelector("button:has-text('Use Service')");
  }

  async goToPlaygroundButton() {
    await this.page.click("button:has-text('Go to Playground')");
  }
}