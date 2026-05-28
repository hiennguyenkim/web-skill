const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

(async () => {
  console.log('🚀 Starting Automated Playwright Browser Test...');
  
  // 1. Ensure playwright is installed
  try {
    require.resolve('playwright');
  } catch (e) {
    console.log('📦 Playwright is not installed. Installing playwright and downloading chromium headlessly...');
    try {
      // Check if package.json exists in process.cwd() or root
      const packageJsonPath = path.resolve(process.cwd(), 'package.json');
      if (!fs.existsSync(packageJsonPath)) {
        console.log('📄 package.json not found, initializing standard package...');
        execSync('npm init -y', { stdio: 'ignore' });
      }
      console.log('Installing playwright package...');
      execSync('npm install playwright --no-save', { stdio: 'inherit' });
      console.log('Installing chromium browser binaries...');
      execSync('npx playwright install chromium', { stdio: 'inherit' });
      console.log('✅ Playwright dependencies installed successfully.');
    } catch (installErr) {
      console.error('❌ Failed to install Playwright dependencies automatically:', installErr);
      process.exit(1);
    }
  }

  // Require playwright dynamically after installation
  const { chromium } = require('playwright');
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // Capture and track console errors
    const consoleErrors = [];
    page.on('pageerror', (exception) => {
      consoleErrors.push(exception.toString());
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(`Console error: ${msg.text()}`);
      }
    });

    // Resolve local HTML file path robustly
    let filePath = path.resolve(process.cwd(), 'index.html');
    if (!fs.existsSync(filePath)) {
      filePath = path.resolve(__dirname, 'index.html');
    }
    if (!fs.existsSync(filePath)) {
      filePath = path.resolve(__dirname, '../index.html');
    }
    
    if (!fs.existsSync(filePath)) {
      console.error(`❌ Error: index.html not found at process root or template root.`);
      process.exit(1);
    }
    
    console.log(`🔗 Loading local page: file://${filePath}`);
    await page.goto(`file://${filePath}`);
    await page.waitForLoadState('networkidle');

    // Make sure assets folder exists and save verification screenshot robustly
    let assetsDir = path.resolve(process.cwd(), 'assets');
    if (!fs.existsSync(assetsDir) && fs.existsSync(path.resolve(__dirname, '../assets'))) {
      assetsDir = path.resolve(__dirname, '../assets');
    } else if (!fs.existsSync(assetsDir)) {
      fs.mkdirSync(assetsDir, { recursive: true });
    }
    
    const screenshotPath = path.resolve(assetsDir, 'verification_screenshot.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`📸 Full-page verification screenshot saved to: ${screenshotPath}`);

    // Standard DOM checks
    const title = await page.title();
    console.log(`📄 Page Title: "${title}"`);
    
    const h1Count = await page.locator('h1').count();
    console.log(`🏷️  Number of H1 elements: ${h1Count}`);
    
    const navCount = await page.locator('nav, header').count();
    console.log(`🧱 Navigation/Header elements found: ${navCount}`);

    // Verify no console errors occurred
    if (consoleErrors.length > 0) {
      console.error('❌ Test Failed: Console errors detected during execution:');
      consoleErrors.forEach((err) => console.error(`  - ${err}`));
      process.exit(1);
    }

    console.log('✅ Test Passed: No console or syntax errors detected in browser.');
    process.exit(0);
  } catch (error) {
    console.error('❌ Test Execution Failed:', error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
})();
