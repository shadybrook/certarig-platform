import { defineConfig } from "@playwright/test";

const PORT = Number(process.env.CERTARIG_E2E_PORT || 18080);

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  webServer: {
    command: `cd .. && $(test -x .venv/bin/python && echo .venv/bin/python || echo python3) -m certarig sim serve --port ${PORT} --evidence-dir /tmp/certarig-e2e-${PORT}`,
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
