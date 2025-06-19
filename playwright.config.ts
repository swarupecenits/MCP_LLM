import { defineConfig, devices } from "@playwright/test";
import { timeouts } from "./constants.ts";

const environment: string = (process.env.ENVIRONMENT || "local").trim();
const validEnvironments = ["prod", "int", "dev", "local", "canary"];
if (!validEnvironments.includes(environment)) {
  throw new Error(`Invalid environment: ${environment}. Expected one of ${validEnvironments.join(", ")}`);
}
const tag: string = (process.env.TAG || "").trim();
const resultsPrefix = tag ? `${tag}-${environment}` : `${environment}`;

const baseUrlMap = {
  prod: "https://ai.azure.com/",
  int: "https://int.ai.azure.com/",
  dev: "https://dev.ai.azure.com/",
  local: "https://dev.ai.azure.com/",
  canary: "https://eastus2euap.ai.azure.com/",
};

const oaiBaseUrlMap = {
  prod: "https://oai.azure.com/",
  int: "https://int.oai.azure.com/",
  dev: "https://dev.oai.azure.com/",
  local: "https://dev.oai.azure.com/",
  canary: "https://canary.oai.azure.com/",
};

const defaultConfig = {
  testDir: "./tests/",
  /* Run tests in files in parallel */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 1 : 0,
  // Opt out of parallel tests on CI.
  workers: process.env.CI ? 2 : 1,
  // Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions.
  use: {
    // Base URL to use in actions like `await page.goto('/')`.
    baseURL: baseUrlMap[environment],
    // Attribute used for page.getByTestId()
    testIdAttribute: "data-automation-id",
    // Emulates the user locale.
    locale: "en-US",
    // Emulates the user timezone.
    timezoneId: "America/Los_Angeles",
    // Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer
    trace: "on-first-retry",
    // Capture screenshot after each test failure in pipeline.
    screenshot: process.env.CI ? "only-on-failure" : "off",
  },
  expect: {
    // Maximum time expect() should wait for the condition to be met.
    timeout: timeouts.expect,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Configure web servers to start before the tests
  webServer: [
    {
      // Start the token server for authentication
      command: "yarn --cwd ./../../ start-token-server",
      port: 3001,
      timeout: timeouts.setup,
      reuseExistingServer: true,
    },
  ],
  // Reporter to use. See https://playwright.dev/docs/test-reporters
  reporter: [
    ["list"],
    ["html", { outputFolder: `tests-e2e-playwright/test-results/${resultsPrefix}-playwright-report`, open: "never" }],
    ["junit", { outputFile: `tests-e2e-playwright/test-results/${resultsPrefix}-test-results.xml` }],
    ["json", { outputFile: `tests-e2e-playwright/test-results/${resultsPrefix}-test-results.json` }],
  ],
};

const previewAIStudioWebServer = {
  // Start the AI Studio server to serve ai.azure.com
  command: "yarn --cwd ./../../ preview:ai-studio",
  port: 443,
  timeout: timeouts.setup,
  reuseExistingServer: true,
  stdout: "pipe",
};

const startAIStudioWebServer = {
  // Start the AI Studio server to serve ai.azure.com
  command: "yarn --cwd ./../../ start:ai-studio",
  port: 443,
  timeout: timeouts.setup,
  reuseExistingServer: true,
  stdout: "pipe",
};

const localConfig = {
  ...defaultConfig,
  use: {
    ...defaultConfig.use,
    ignoreHTTPSErrors: true,
  },
  webServer: [startAIStudioWebServer, ...defaultConfig.webServer],
};

const devConfig = {
  ...localConfig,
  webServer: [previewAIStudioWebServer, ...defaultConfig.webServer],
};

const configMap = {
  prod: defaultConfig,
  int: defaultConfig,
  dev: devConfig,
  local: localConfig,
};

const config = configMap[environment] || localConfig;

export const oaiBaseURL = oaiBaseUrlMap[environment || "local"];

export default defineConfig(config);
