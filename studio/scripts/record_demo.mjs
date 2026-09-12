/** Record stills and a short stranger-path loop against an already-running sim serve. */
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { launchBrowser, login, waitForEvidenceHash } from "./lib/studio-demo.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.CERTARIG_DEMO_OUT || join(ROOT, "..", "test-results", "demo-film");
const BASE = process.env.CERTARIG_DEMO_URL || "http://127.0.0.1:8082";

mkdirSync(OUT, { recursive: true });

const browser = await launchBrowser(chromium);
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 800 } },
});
const page = await context.newPage();

await login(page, BASE);
await page.waitForTimeout(1200);
await page.screenshot({ path: join(OUT, "01_live_pots.png") });

await page.locator('#nav a[data-view="onboard"]').click();
await page.getByTestId("interview-start").click();
await page.getByTestId("interview-text").fill(
  "ADC pots, E-stop, relay. pressure 4.05 bar, flow 14.5 L/min. observe-only: none. sim-stranger.md"
);
await page.getByTestId("interview-record").click();
await page.getByTestId("interview-prompt").filter({ hasText: "Required facts are in" }).waitFor();
await page.getByTestId("interview-propose").click();
await page.getByTestId("interview-diff").filter({ hasText: "next" }).waitFor({ timeout: 20_000 });
await page.screenshot({ path: join(OUT, "02_onboard_propose.png") });
await page.getByTestId("interview-apply").click();
await page.waitForTimeout(800);
await page.screenshot({ path: join(OUT, "03_onboard_applied.png") });

await page.locator('#nav a[data-view="procedures"]').click();
await page.locator("#proc-id").selectOption("pressure_guardrail");
await page.locator("#proc-start").click();
await page.locator("#active-run").waitFor({ timeout: 15_000 });
await page.getByTestId("trigger-coach").waitFor({ timeout: 15_000 });
await page.screenshot({ path: join(OUT, "04_procedure_running.png") });

await waitForEvidenceHash(page);
await page.screenshot({ path: join(OUT, "05_evidence.png") });

const video = page.video();
await context.close();
await browser.close();
if (video) {
  console.log(JSON.stringify({ ok: true, video: await video.path(), out: OUT }));
} else {
  console.log(JSON.stringify({ ok: true, out: OUT }));
}
