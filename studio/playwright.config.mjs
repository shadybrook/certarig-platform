import { defineConfig } from "@playwright/test";

const PORT = Number(process.env.CERTARIG_E2E_PORT || 18080);

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  webServer: {
    command: `cd .. && mkdir -p /tmp/certarig-e2e-${PORT}-cfg && cp config/rig.sim.json config/capabilities.wave1.json /tmp/certarig-e2e-${PORT}-cfg && $(test -x .venv/bin/python && echo .venv/bin/python || echo python3) -m certarig sim serve --port ${PORT} --config /tmp/certarig-e2e-${PORT}-cfg/rig.sim.json --capabilities /tmp/certarig-e2e-${PORT}-cfg/capabilities.wave1.json --evidence-dir /tmp/certarig-e2e-${PORT}`,
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
