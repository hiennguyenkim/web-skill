const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

(async () => {
  const startTime = Date.now();
  console.log('🚀 Starting Advanced Automated Playwright Browser Test Suite...');
  
  // 1. Ensure Playwright is installed
  try {
    require.resolve('playwright');
  } catch (e) {
    console.log('📦 Playwright is not installed. Installing playwright and downloading chromium headlessly...');
    try {
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
  let assetsDir = path.resolve(process.cwd(), 'assets');
  const testResults = {
    timestamp: new Date().toLocaleString(),
    passed: true,
    viewports: [],
    consoleErrors: [],
    performance: {},
    elements: {},
    errorDetails: null
  };

  try {
    browser = await chromium.launch({ headless: true });
    
    // Resolve local HTML file path robustly
    let filePath = path.resolve(process.cwd(), 'index.html');
    if (!fs.existsSync(filePath)) {
      filePath = path.resolve(__dirname, 'index.html');
    }
    if (!fs.existsSync(filePath)) {
      filePath = path.resolve(__dirname, '../index.html');
    }
    
    if (!fs.existsSync(filePath)) {
      throw new Error('index.html not found in process root or template directories.');
    }
    
    console.log(`🔗 Target HTML File: file://${filePath}`);
    const fileUrl = `file://${filePath}`;

    // Target viewports
    const viewports = [
      { name: 'Desktop', width: 1280, height: 800, isMobile: false },
      { name: 'Mobile', width: 375, height: 812, isMobile: true }
    ];

    // Ensure assets folder exists
    if (!fs.existsSync(assetsDir) && fs.existsSync(path.resolve(__dirname, '../assets'))) {
      assetsDir = path.resolve(__dirname, '../assets');
    } else if (!fs.existsSync(assetsDir)) {
      fs.mkdirSync(assetsDir, { recursive: true });
    }

    // Run test for each viewport
    for (const vp of viewports) {
      console.log(`🖥️  Testing Viewport: ${vp.name} (${vp.width}x${vp.height})`);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        isMobile: vp.isMobile
      });
      const page = await context.newPage();

      // Monitor console errors and crashes
      page.on('pageerror', (exception) => {
        const errMsg = `[${vp.name}] Runtime error: ${exception.toString()}`;
        testResults.consoleErrors.push(errMsg);
        console.error(`❌ ${errMsg}`);
        testResults.passed = false;
      });
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const errMsg = `[${vp.name}] Console error: ${msg.text()}`;
          testResults.consoleErrors.push(errMsg);
          console.error(`⚠️  ${errMsg}`);
        }
      });

      await page.goto(fileUrl);
      await page.waitForLoadState('networkidle');

      // Check for horizontal scrolling (layout overflow)
      const hasOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      
      if (hasOverflow && vp.name === 'Mobile') {
        const warnMsg = `[Mobile] Visual Layout Warning: Horizontal scrolling detected. Mobile layout should fit within viewport width.`;
        testResults.consoleErrors.push(warnMsg);
        console.warn(`⚠️  ${warnMsg}`);
      }

      // Take screenshot
      const screenshotFilename = `verification_${vp.name.toLowerCase()}.png`;
      const screenshotPath = path.resolve(assetsDir, screenshotFilename);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`📸 Screenshot saved: ${screenshotPath}`);

      testResults.viewports.push({
        name: vp.name,
        width: vp.width,
        height: vp.height,
        screenshot: `./assets/${screenshotFilename}`,
        hasOverflow
      });

      // Extract details only once (on Desktop run)
      if (vp.name === 'Desktop') {
        // Measure performance metrics
        testResults.performance = await page.evaluate(() => {
          const t = window.performance.timing;
          if (!t) return { ttfb: 0, domLoaded: 0, loadTime: 0 };
          return {
            ttfb: Math.max(0, t.responseStart - t.requestStart),
            domLoaded: Math.max(0, t.domContentLoadedEventEnd - t.navigationStart),
            loadTime: Math.max(0, t.loadEventEnd - t.navigationStart)
          };
        });

        // Structure counts
        testResults.elements = await page.evaluate(() => {
          return {
            title: document.title,
            h1Count: document.querySelectorAll('h1').length,
            navCount: document.querySelectorAll('nav, header').length,
            buttonCount: document.querySelectorAll('button, a.btn, .button').length,
            sectionCount: document.querySelectorAll('section, main, article').length,
            imgCount: document.querySelectorAll('img').length
          };
        });
      }

      await context.close();
    }

  } catch (error) {
    testResults.passed = false;
    testResults.errorDetails = error.message;
    console.error('❌ Test execution encountered a critical error:', error);
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  // 2. Generate Interactive Glassmorphic HTML Report
  const totalDuration = ((Date.now() - startTime) / 1000).toFixed(2);
  const statusColor = testResults.passed ? '#10b981' : '#ef4444';
  const statusText = testResults.passed ? 'PASSED' : 'FAILED';
  
  const reportHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Automation Test Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090a0f;
      --card-bg: rgba(19, 21, 32, 0.6);
      --card-border: rgba(255, 255, 255, 0.05);
      --accent: #a78bfa;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --success: #10b981;
      --error: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 2.5rem;
      background-image: radial-gradient(circle at 10% 20%, rgba(167, 139, 250, 0.05) 0%, transparent 40%),
                        radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.03) 0%, transparent 40%);
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 1.5rem;
    }
    h1, h2, h3 { font-family: 'Outfit', sans-serif; }
    .status-badge {
      padding: 0.5rem 1.5rem;
      border-radius: 9999px;
      font-weight: 800;
      letter-spacing: 0.05em;
      border: 1px solid;
      background: rgba(16, 185, 129, 0.1);
      color: var(--success);
    }
    .status-badge.failed {
      background: rgba(239, 68, 68, 0.1);
      color: var(--error);
    }
    .dashboard-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.5rem;
      backdrop-filter: blur(12px);
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .card:hover {
      transform: translateY(-2px);
      border-color: rgba(167, 139, 250, 0.2);
    }
    .metric-value {
      font-size: 2rem;
      font-weight: 800;
      color: var(--accent);
      margin-top: 0.5rem;
      font-family: 'Outfit', sans-serif;
    }
    .gallery {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }
    @media (max-width: 768px) {
      .gallery { grid-template-columns: 1fr; }
    }
    .screenshot-container {
      text-align: center;
    }
    .screenshot-container img {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      margin-top: 1rem;
      cursor: pointer;
    }
    .console-log {
      max-height: 250px;
      overflow-y: auto;
      background: rgba(0, 0, 0, 0.3);
      padding: 1rem;
      border-radius: 8px;
      font-family: monospace;
      font-size: 0.875rem;
      border: 1px solid rgba(255, 255, 255, 0.05);
      margin-top: 1rem;
    }
    .console-log-item {
      padding: 0.35rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.02);
      color: #fbbf24;
    }
    .console-log-item.error { color: var(--error); }
    .structure-list {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
      margin-top: 1rem;
    }
    .structure-item {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .info-footer {
      text-align: center;
      margin-top: 3rem;
      color: var(--text-muted);
      font-size: 0.875rem;
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1 style="font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Automation Audit</h1>
      <p style="color: var(--text-muted); margin-top: 0.25rem;">Timestamp: ${testResults.timestamp} | Duration: ${totalDuration}s</p>
    </div>
    <div class="status-badge ${testResults.passed ? '' : 'failed'}">
      ${statusText}
    </div>
  </header>

  <main>
    ${testResults.errorDetails ? `
    <div class="card" style="border-color: var(--error); margin-bottom: 2rem;">
      <h3 style="color: var(--error); margin-bottom: 0.5rem;">🚨 Critical Execution Failure</h3>
      <p style="font-family: monospace;">${testResults.errorDetails}</p>
    </div>
    ` : ''}

    <div class="dashboard-grid">
      <div class="card">
        <h3>Page Title</h3>
        <p class="metric-value" style="font-size: 1.25rem; font-weight: 600; margin-top: 1rem;">"${testResults.elements.title || 'N/A'}"</p>
      </div>
      <div class="card">
        <h3>Browser DOM Load Time</h3>
        <p class="metric-value">${testResults.performance.loadTime ? testResults.performance.loadTime + ' ms' : 'Fast (<50ms)'}</p>
      </div>
      <div class="card">
        <h3>Time to First Byte (TTFB)</h3>
        <p class="metric-value">${testResults.performance.ttfb ? testResults.performance.ttfb + ' ms' : 'Local File'}</p>
      </div>
      <div class="card">
        <h3>Console Violations</h3>
        <p class="metric-value" style="color: ${testResults.consoleErrors.length > 0 ? 'var(--error)' : 'var(--success)'}">
          ${testResults.consoleErrors.length}
        </p>
      </div>
    </div>

    <div class="gallery">
      ${testResults.viewports.map(vp => `
      <div class="card screenshot-container">
        <h3>${vp.name} Viewport (${vp.width}x${vp.height})</h3>
        ${vp.hasOverflow ? '<span style="color: var(--error); font-size: 0.8rem; font-weight: 600;">⚠️ Horizontal Layout Overflow</span>' : ''}
        <a href="${vp.screenshot}" target="_blank">
          <img src="${vp.screenshot}" alt="${vp.name} Screenshot">
        </a>
      </div>
      `).join('')}
    </div>

    <div class="dashboard-grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card">
        <h3>Page Structure Audit</h3>
        <div class="structure-list">
          <div class="structure-item"><span>H1 Headers</span><strong>${testResults.elements.h1Count || 0}</strong></div>
          <div class="structure-item"><span>Nav/Header Blocks</span><strong>${testResults.elements.navCount || 0}</strong></div>
          <div class="structure-item"><span>CTA Buttons/Links</span><strong>${testResults.elements.buttonCount || 0}</strong></div>
          <div class="structure-item"><span>Semantic Sections</span><strong>${testResults.elements.sectionCount || 0}</strong></div>
        </div>
      </div>
      <div class="card">
        <h3>Console & Layout Logs</h3>
        ${testResults.consoleErrors.length === 0 ? `
          <p style="color: var(--success); font-weight: 600; margin-top: 1.5rem;">✅ No errors or layout overflows detected in the browser console.</p>
        ` : `
          <div class="console-log">
            ${testResults.consoleErrors.map(err => `
              <div class="console-log-item ${err.includes('error') || err.includes('Runtime') ? 'error' : ''}">
                ${err}
              </div>
            `).join('')}
          </div>
        `}
      </div>
    </div>
  </main>

  <footer class="info-footer">
    <p>Powered by Playwright & GSD Web Creator Automation Engine</p>
  </footer>
</body>
</html>`;

  const reportPath = path.resolve(assetsDir, 'test_report.html');
  fs.writeFileSync(reportPath, reportHtml);
  console.log(`📄 Glassmorphic HTML Test Report generated at: ${reportPath}`);

  if (!testResults.passed) {
    console.error('❌ Test Suite Finished: Verification FAILED.');
    process.exit(1);
  } else {
    console.log('✅ Test Suite Finished: Verification PASSED.');
    process.exit(0);
  }
})();
