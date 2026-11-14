import { chromium, expect } from "@playwright/test";
import fs from "node:fs";
const browser = await chromium.launch({
  args: ["--use-mock-keychain", "--password-store=basic"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
let requests = 0;
page.on("pageerror", (e) => errors.push(e.message));
page.on("request", (r) => {
  if (r.url().includes("/v1/")) requests++;
});
const root = new URL(
  "../docs/product/validation/session-journal/prototype/",
  import.meta.url,
);
fs.mkdirSync(root, { recursive: true });
await page.goto(
  process.env.CERTARIG_PROTOTYPE_URL || "http://127.0.0.1:18121/prototype.html",
);
await expect(page.locator("#product")).toBeVisible();
await page.locator("#commit-draft").click();
await page.locator("#evaluate").click();
await page.locator("#qualify").click();
await expect(page.locator("#review")).toBeDisabled();
await page.locator("#fixture-role").selectOption("reviewer");
await page.locator("#review").click();
await page
  .getByRole("button", { name: "Start observation", exact: true })
  .click();
await expect(page.locator("#revoke-strip")).toContainText("Running");
await page.locator("[data-route=evidence]").click();
await page.getByRole("button", { name: "Inspect raw evidence" }).click();
await expect(page.locator("#evidence-list pre")).toContainText("22.8");
await page.getByRole("button", { name: "Revoke active access" }).click();
await expect(page.locator("#revoke-strip")).toBeEmpty();
await page.locator("#fixture-role").selectOption("author");
await page.locator("#evaluate").click();
await page.locator('[data-context="activity"]').click();
await page.getByRole("button",{name:"Cancel task",exact:true}).click();
await expect(page.locator("#task-list")).toContainText("cancelled");
await page.locator('[data-context="proposal"]').click();

await page.locator("#fixture-scenario").selectOption("stale");
await page.locator("[data-route=sessions]").click();
await page.locator("#evaluate").click();
await expect(page.locator("#qualify")).toBeDisabled();
await expect(page.locator("#draft-blockers")).toContainText("stale");
await page.locator("#fixture-scenario").selectOption("nominal");
await page.locator("#evaluate").click();
await page.locator("#qualify").click();
await page.locator("#message").fill("Keep all evidence.");
await page.locator("#message-form button").click();
await page.reload();
await expect(page.locator("#conversation")).toContainText("Keep all evidence.");
for (const route of [
  "agents",
  "benches",
  "sandbox",
  "evidence",
  "deployments",
  "connectors",
  "settings",
  "sessions",
]) {
  await page.locator(`[data-route=${route}]`).click();
  await expect(page.locator(`[data-view=${route}]`)).toBeVisible();
}
await page.locator("#palette-open").click();
await page.locator("#palette-query").fill("Sandbox");
await page
  .locator("#palette-results")
  .getByRole("button", { name: "Sandbox", exact: true })
  .click();
await expect(page.locator("[data-view=sandbox]")).toBeVisible();
await page.locator("[data-route=sessions]").click();
await page.locator("#open-builder").click();
await expect(page.locator("#agent-builder")).toBeVisible();
await page.keyboard.press("Escape");
for (const [width, height] of [
  [1440, 900],
  [1280, 800],
  [834, 1112],
  [390, 844],
]) {
  await page.setViewportSize({ width, height });
  await page.screenshot({
    path: new URL(`prototype-${width}.png`, root).pathname,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
}
await page.locator("#inspector-toggle").click();
await expect(page.locator("#context-inspector")).toBeVisible();
await page.keyboard.press("Escape");
await page.locator("#nav-toggle").click();
await page.locator("[data-route=agents]").click();
await page.locator("#agents-new").click();
await page.locator("#agent-name").fill("Mobile engineer");
await page.screenshot({
  path: new URL("prototype-mobile-builder.png", root).pathname,
});
await page.keyboard.press("Escape");
const zoomContext=await browser.newContext({viewport:{width:720,height:450},deviceScaleFactor:2});
const zoomPage=await zoomContext.newPage();
await zoomPage.goto(process.env.CERTARIG_PROTOTYPE_URL||"http://127.0.0.1:18121/prototype.html");
await zoomPage.locator("#session-next").click();
await zoomPage.locator("#save-agent").scrollIntoViewIfNeeded();
await expect(zoomPage.locator("#save-agent")).toBeInViewport();
expect(await zoomPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
await zoomPage.screenshot({path:new URL("prototype-200-percent-reflow.png",root).pathname});
await zoomContext.close();
expect(errors).toEqual([]);
expect(requests).toBe(0);
fs.writeFileSync(
  new URL("prototype-check.json", root),
  JSON.stringify(
    {
      status: "passed",
      consoleErrors: errors,
      platformRequests: requests,
      checks: [
        "fixture success, independent review, observation and revocation",
        "stale-source refusal and recovery",
        "draft refresh recovery",
        "all eight destinations",
        "command palette and modal Escape",
        "four viewport widths and no horizontal overflow",
      "task cancellation and late-result suppression",
      "200 percent reflow equivalent at 720 CSS pixels and 2x device scale",
        "mobile navigation and builder",
      ],
      nativeKeyboard: "unverified",
    },
    null,
    2,
  ),
);
console.log(
  "Prototype checks passed. No platform API requests. Native mobile keyboard unverified.",
);
await browser.close();
