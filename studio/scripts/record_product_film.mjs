/** 90-second silent product film with captions. Film the product that exists. */
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  clock,
  hideCard,
  injectOverlays,
  launchBrowser,
  login,
  showCaption,
  showCard,
  waitForEvidenceHash,
} from "./lib/studio-demo.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const OUT = process.env.CERTARIG_DEMO_OUT || join(ROOT, "..", "test-results", "product-film");
const BASE = process.env.CERTARIG_DEMO_URL || "http://127.0.0.1:8082";

mkdirSync(OUT, { recursive: true });

const browser = await launchBrowser(chromium);
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 800 } },
});
const page = await context.newPage();
await login(page, BASE);
await injectOverlays(page);
const until = clock();

await showCard(page, {
  kicker: "The problem",
  title: "Test benches still run on memory.",
  end: "One person. No checksum. No map.",
});
await until(page, 12_000);

await showCard(page, {
  kicker: "CertaRig",
  title: "The model asks. The kernel decides.",
});
await until(page, 18_000);

await hideCard(page);
await page.locator('#nav a[data-view="telemetry"]').click();
await showCaption(page, "Kernel owns the numbers.");
await page.waitForTimeout(800);
await page.screenshot({ path: join(OUT, "live_pots.png") });
await until(page, 38_000);

await page.locator('#nav a[data-view="onboard"]').click();
await showCaption(page, "A human applies the map.");
await page.getByTestId("interview-start").click();
await page.getByTestId("interview-text").fill(
  "ADC pots, E-stop, relay. pressure 4.05 bar, flow 14.5 L/min. observe-only: none. sim-stranger.md"
);
await page.getByTestId("interview-record").click();
await page.getByTestId("interview-prompt").filter({ hasText: "Required facts are in" }).waitFor();
await page.getByTestId("interview-propose").click();
await page.getByTestId("interview-diff").filter({ hasText: "next" }).waitFor({ timeout: 20_000 });
await page.screenshot({ path: join(OUT, "interview_propose.png") });
await page.getByTestId("interview-apply").click();
await page.waitForTimeout(600);
await until(page, 62_000);

await page.locator('#nav a[data-view="procedures"]').click();
await showCaption(page, "Approved procedures only.");
await page.locator("#proc-id").selectOption("pressure_guardrail");
await page.locator("#proc-start").click();
await page.locator("#active-run").waitFor({ timeout: 15_000 });
await page.getByTestId("trigger-coach").waitFor({ timeout: 15_000 });
await page.screenshot({ path: join(OUT, "trigger_coach.png") });
await until(page, 78_000);

await showCaption(page, "Checksummed evidence.");
await waitForEvidenceHash(page);
await page.screenshot({ path: join(OUT, "evidence_hash.png") });
await until(page, 86_000);

await showCard(page, {
  kicker: "CertaRig",
  title: "The model asks. The kernel decides.",
  end: "certarig.dev",
});
await until(page, 90_000);

const video = page.video();
await context.close();
await browser.close();
const path = video ? await video.path() : null;
console.log(JSON.stringify({ ok: true, video: path, out: OUT }));
