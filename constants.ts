// Query parameter used to allow tests to use authentication from the token server.
export const authParam = "auth=local";

// Maximum time for Playwright to wait for operations to complete, measured in milliseconds.
export const timeouts = {
  expect: 10000, // Time for an expect() assertion, i.e. isVisible().
  slowExpect: 30000, // Time for a slow expect() assertion, i.e. isVisible().
  test: 30000, // Time for a test operation, i.e. page.goto().
  search: 60000, // Time for a search operation, i.e. model catalog filtering.
  setup: 120000, // Maximum time to wait for test setup, i.e. yarn start-token-server.
  slowTest: 180000, // Maximum time to wait for a whole test.
  lro: 5 * 60000, // Time for a long-running operation to timeout, i.e. project creation.
  verySlow: 600000, // Time for a very slow operation, i.e. model deployment.
};

// Static params of resources to be replaced with Test Subscription values
export const testConfig = {
  subscriptionId: "d5320f9a-73da-4a74-b639-83efebc7bb6f",
  subscriptionName: "AML - Experiences - Static Resources",
  resourceGroup: "aml-e2e-July-15-2024",
  location: "East US",
  tenantId: "72f988bf-86f1-41af-91ab-2d7cd011db47",
  staticHub: "e2e-test-static-hub",
  staticProject: "e2e-test-static-project",
  staticHubSecondary: "e2e-test-static-hub-2",
  staticProjectSecondary: "e2e-test-static-project-2",
  staticProjecttertiary: "v-zhaod-8439",
  staticStorage: "e2eteststaticstorage",
  staticContainer: "e2eteststaticcontainer",
  staticAOAIResource: "e2e-test-static-aoai",
  // Secondary AOAI resource used for scenarios such as failover testing, multi-region support, or A/B testing.
  staticAOAIResourceSecondary: "e2e-test-static-aoai-2",
  // This data only use to create new azure open ai connection, need to be deleted after test
  staticAOAIResourceTertiary: "e2e-test-static-aoai-3",
  // The original name cannot be displayed in the list, so it cannot be selected. However, when I create a new item with the same name as the original, the creation process is successful, but the data still does not appear in the list. I have created a bug to track this issue.
  staticDataConnection: "e2eteststaticconnection",
  staticData: "static-data",
};

// Temporary params for Playground resources until Test subscription can use AOAI
export const playgroundTestConfig = {
  ...testConfig,
  resourceGroup: "rg-pritamdai",
  subscriptionId: "2d385bf4-0756-4a76-aa95-28bf9ed3b625",
  workspace: "pritamd_ai-eastus2",
  connection: "ai-pritamdaieastus2744192167360_aoai",
  deploymentName: "gpt-4",
};

export const aoaiMonitorConfig = {
  // https://int.ai.azure.com/resource/deployments?wsid=/subscriptions/1b9435b6-a98e-47dd-8cfc-50eb9fb58af0/resourceGroups/aoai-abuse-rg/providers/Microsoft.CognitiveServices/accounts/rai-abuse-validator-use&tid=72f988bf-86f1-41af-91ab-2d7cd011db47
  ...testConfig,
  resourceGroup: "aoai-abuse-rg",
  subscriptionId: "1b9435b6-a98e-47dd-8cfc-50eb9fb58af0",
  workspace: "rai-abuse-validator-use",
};

export const resourceBlocklistConfig = {
  // https://int.ai.azure.com/resource/overview?wsid=/subscriptions/c830bb7a-83f5-45e3-81fc-3c2053e7d16f/resourceGroups/rai-ux/providers/Microsoft.CognitiveServices/accounts/rai-ux-e2e-test&flight=AiStudioDarkMode&tid=72f988bf-86f1-41af-91ab-2d7cd011db47&mode=switch
  ...testConfig,
  resourceGroup: "rai-ux",
  subscriptionId: "c830bb7a-83f5-45e3-81fc-3c2053e7d16f",
  resource: "rai-ux-e2e-test",
};

export const projectBlocklistConfig = {
  // https://int.ai.azure.com/contentfilters/blocklist?wsid=/subscriptions/c830bb7a-83f5-45e3-81fc-3c2053e7d16f/resourceGroups/rg-yangyang-3940_ai/providers/Microsoft.MachineLearningServices/workspaces/yangyang-1278&flight=AiStudioDarkMode&tid=72f988bf-86f1-41af-91ab-2d7cd011db47&mode=switch
  ...testConfig,
  resourceGroup: "rg-yangyang-3940_ai",
  subscriptionId: "c830bb7a-83f5-45e3-81fc-3c2053e7d16f",
  workspace: "yangyang-1278",
};

// Temporary params for AYD Playground resources
export const aydPlaygroundTestConfig = {
  ...testConfig,
  resourceGroup: "ppidatala_rg",
  subscriptionId: "b72743ec-8bb3-453f-83ad-a53e8a50712e",
  workspace: "ppidatala-3953",
  deploymentWorkspace: "pidatala_defaultless3",
  connection: "CLUGPTModel",
  deploymentName: "gptturbo",
};

export const scopes = {
  hub: "Hub",
  project: "Project",
  global: "Global",
  resource: "Resource",
};

// Static params of resources for evaluation tests
export const evaluationTestConfig = {
  ...testConfig,
  datasetName: "cyan_drawer_0p54qfg8gz (version 1)",
  deploymentNameDisabled: "evaluation-e2e-test-deployment",
  deploymentNameEnabled: "aml-e2e-playground-deployment-e",
  promptFlowName: "evaluation-e2e-test-pf",
  staticProject: "aml-e2e-playground",
};

export const modelVersions = {
  llama27bChat: "23",
  gpt4o: "1",
  mistralLarge: "1",
};
