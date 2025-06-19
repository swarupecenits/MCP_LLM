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
