const { chromium } = require('playwright');
const { execSync } = require('child_process');

(async () => {
  // Log in using Azure CLI with service principal
  try {
    console.log('Logging in with Azure CLI...');
    execSync('az login --service-principal -u $AZURE_CLIENT_ID -p $AZURE_CLIENT_SECRET --tenant $AZURE_TENANT_ID', { stdio: 'inherit' });
    console.log('Azure CLI login successful');
  } catch (error) {
    console.error('Azure CLI login failed:', error.message);
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to Azure AI portal
  try {
    await page.goto('https://ai.azure.com', { waitUntil: 'networkidle' });
    // Wait for authentication redirect or portal dashboard
    await page.waitForURL(/.*ai\.azure\.com.*/, { timeout: 30000 });
    console.log('Authentication successful, portal loaded');
  } catch (error) {
    console.error('Authentication failed or portal did not load:', error.message);
    await browser.close();
    process.exit(1);
  }

  // Save authenticated session
  await context.storageState({ path: 'auth/storageState.json' });
  console.log('✅ Auth state saved to auth/storageState.json');

  await browser.close();
})();