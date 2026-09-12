/** Slower operator walkthrough. Voiceover lives in docs/go-public/operator-walkthrough.md. */
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  BENCH_DUMP,
  clock,
  injectOverlays,
  launchBrowser,
  showCaption,
  waitForEvidenceHash,
} from "./lib/studio-demo.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.CERTARIG_DEMO_OUT || join(ROOT, "..", "test-results", "operator-walkthrough");
const BASE = process.env.CERTARIG_DEMO_URL || "http://127.0.0.1:8082";

mkdirSync(OUT, { recursive: true });

const browser = await launchBrowser(chromium);
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 800 } },
});
const page = await context.newPage();

const until = clock();
await page.goto(`${BASE}/`);
await injectOverlays(page);
await showCaption(page, "Demo operator key. It stays in this tab. Never in git.");
await page.getByTestId("operator-key").fill("sim-operator-key-000001");
await page.waitForTimeout(2_000);
await page.getByRole("button", { name: "Open Studio" }).click();
await page.locator("#health-pill").waitFor({ state: "visible", timeout: 15_000 });
await until(page, 20_000);

await page.locator('#nav a[data-view="telemetry"]').click();
await showCaption(page, "Live: two channels, trip lines, ready-to-arm. Kernel owns the numbers.");
await page.screenshot({ path: join(OUT, "live.png") });
await until(page, 50_000);

await page.locator('#nav a[data-view="onboard"]').click();
await page.getByTestId("interview-start").waitFor();
await page.waitForTimeout(400);
await showCaption(page, "Onboard. Start. One bench dump. Record facts.");
await page.getByTestId("interview-start").click();
await page.getByTestId("interview-needs").filter({ hasText: "modules" }).waitFor();
await page.getByTestId("interview-text").fill(BENCH_DUMP);
await page.waitForTimeout(1_500);
await page.getByTestId("interview-text").fill(BENCH_DUMP);
await page.getByTestId("interview-record").click();
await page.getByTestId("interview-prompt").filter({ hasText: "Required facts are in" }).waitFor();
await until(page, 90_000);

await showCaption(page, "Propose the map. A human still has to Confirm apply.");
await page.getByTestId("interview-propose").click();
await page.getByTestId("interview-diff").filter({ hasText: "next" }).waitFor({ timeout: 20_000 });
await page.screenshot({ path: join(OUT, "propose.png") });
await until(page, 115_000);

await showCaption(page, "Confirm apply. Interview never arms the relay.");
await page.getByTestId("interview-apply").click();
await page.waitForTimeout(800);
await until(page, 130_000);

await page.locator('#nav a[data-view="procedures"]').click();
await showCaption(page, "Start pressure_guardrail. Read the trigger coach: which pot, live vs target.");
await page.locator("#proc-id").selectOption("pressure_guardrail");
await page.locator("#proc-start").click();
await page.locator("#active-run").waitFor({ timeout: 15_000 });
await page.getByTestId("trigger-coach").waitFor({ timeout: 15_000 });
await page.screenshot({ path: join(OUT, "coach.png") });
await until(page, 190_000);

await showCaption(page, "Evidence. Export the bundle. Open the SHA-256. interview.json is inside.");
await waitForEvidenceHash(page);
await page.getByText(".zip").first().waitFor({ timeout: 15_000 });
await page.waitForTimeout(800);
await page.screenshot({ path: join(OUT, "evidence.png") });
await until(page, 230_000);

await showCaption(page, "That is the loop. Simulator first. Kernel decides.");
await until(page, 240_000);

const video = page.video();
await context.close();
await browser.close();
const path = video ? await video.path() : null;
console.log(JSON.stringify({ ok: true, video: path, out: OUT }));
