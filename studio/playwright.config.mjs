import { defineConfig } from "@playwright/test";
import { copyFileSync, existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PORT = Number(process.env.CERTARIG_E2E_PORT || 18080);
const ROOT = fileURLToPath(new URL("../", import.meta.url));
// Reviews and approvals intentionally survive restarts. Each suite needs its
// own state so a previous accepted configuration cannot satisfy this run.
const runtime = mkdtempSync(path.join(tmpdir(), "certarig-e2e-"));
for (const file of ["rig.sim.json", "capabilities.wave1.json"]) {
  copyFileSync(path.join(ROOT, "config", file), path.join(runtime, file));
}
const python = existsSync(path.join(ROOT, ".venv/bin/python"))
  ? path.join(ROOT, ".venv/bin/python") : "python3";
const quote = (value) => `'${String(value).replaceAll("'", "'\\''")}'`;

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
    cwd: ROOT,
    command: `${quote(python)} -m certarig sim serve --port ${PORT} --config ${quote(path.join(runtime, "rig.sim.json"))} --capabilities ${quote(path.join(runtime, "capabilities.wave1.json"))} --evidence-dir ${quote(path.join(runtime, "evidence"))}`,
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
