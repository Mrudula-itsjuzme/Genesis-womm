import { defineConfig } from '@playwright/test';
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3000';
export default defineConfig({
  testDir: process.env.PLAYWRIGHT_LIVE === '1' ? './tests/live' : './tests/browser',
  fullyParallel: true,
  use: { baseURL, headless: true },
  reporter: 'list',
  outputDir: '../../scratch/playwright-results',
  webServer: { command: 'npm run dev -- --hostname 127.0.0.1 --port ' + new URL(baseURL).port, url: baseURL, reuseExistingServer: !process.env.CI, timeout: 120000 },
});
