import { defineConfig } from '@playwright/test';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const runtime = process.env.CERTARIG_BROWSER_FIXTURE_ROOT ||= mkdtempSync(path.join(tmpdir(), 'certarig-customer-browser-'));
const python = existsSync(path.join(root,'.venv/bin/python')) ? path.join(root,'.venv/bin/python') : 'python3';
const quote = (value) => `'${String(value).replaceAll("'", "'\\''")}'`;
export default defineConfig({
  testDir: './tests-platform', outputDir: './test-results-platform', timeout: 40000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:18095', headless: true, trace: 'retain-on-failure' },
  reporter: [['list']],
  webServer: { cwd: root, command: `${quote(python)} -m tests.platform.browser_server ${quote(runtime)}`, url: 'http://127.0.0.1:18095', reuseExistingServer: false, timeout: 20000 },
});
