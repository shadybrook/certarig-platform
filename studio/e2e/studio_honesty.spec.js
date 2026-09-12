import { expect, test } from "@playwright/test";

const OPERATOR = "sim-operator-key-000001";

async function login(page) {
  await page.goto("/");
  await page.getByTestId("operator-key").fill(OPERATOR);
  await page.getByRole("button", { name: "Open Studio" }).click();
  await expect(page.locator("#health-pill")).toHaveAttribute("data-state", "ok", { timeout: 15_000 });
}

async function contractHeaders(request) {
  const rig = await (
    await request.get("/v1/rig", { headers: { "X-CertaRig-Operator-Key": OPERATOR } })
  ).json();
  return {
    "X-CertaRig-Operator-Key": OPERATOR,
    "X-CertaRig-Contract": rig.contract_hash,
    "Content-Type": "application/json",
  };
}

test("onboard briefing persists after reload", async ({ page }) => {
  await login(page);
  await page.locator('#nav a[data-view="onboard"]').click();
  await page.getByTestId("brief-p1").fill("P1 pressure emulator");
  await page.getByTestId("brief-p2").fill("P2 flow emulator");
  await page.getByTestId("brief-estop").fill("GPIO24 mushroom");
  await page.getByTestId("brief-relay").fill("GPIO23 permit");
  await page.getByTestId("brief-notes").fill("wave-1 as-built");
  await page.locator("#brief-save").click();
  await expect(page.getByTestId("brief-status")).toContainText("Saved");
  await page.reload();
  await expect(page.locator("#health-pill")).toHaveAttribute("data-state", "ok", { timeout: 15_000 });
  await page.locator('#nav a[data-view="onboard"]').click();
  await expect(page.getByTestId("brief-p1")).toHaveValue("P1 pressure emulator");
  await expect(page.getByTestId("brief-p2")).toHaveValue("P2 flow emulator");
});

test("stale contract retries once after a hot apply", async ({ page, request }) => {
  await login(page);
  const rig = await (await request.get("/v1/rig", { headers: { "X-CertaRig-Operator-Key": OPERATOR } })).json();
  const document = { ...rig.document, abort_limits: { pressure: 4.15, flow: 15.0 } };
  delete document.pressure_abort_bar;
  await request.post("/v1/rig/apply", {
    headers: await contractHeaders(request),
    data: { document, expected_current_hash: rig.config_hash },
  });
  await page.locator("#cmd-safe").click();
  await expect(page.locator("#toast")).toBeHidden({ timeout: 5_000 });
  await expect(page.locator("#health-pill")).toHaveAttribute("data-state", "ok");
});

test("authoring wizard drafts and approves a soak", async ({ page }) => {
  await login(page);
  await page.locator('#nav a[data-view="author"]').click();
  await page.getByTestId("author-template").selectOption("soak");
  await page.getByTestId("author-signal").selectOption("pressure_emulator");
  await page.locator("#author-validate").click();
  await expect(page.locator("#author-errors")).toContainText("Valid");
  await page.locator("#author-draft").click();
  await expect(page.locator("[data-draft]")).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Approve" }).click();
  await page.locator('#nav a[data-view="procedures"]').click();
  await expect(page.locator('#proc-id option[value="pressure_emulator_soak"]')).toHaveCount(1);
});

test("procedures reconnect to the stored run after reload", async ({ page, request }) => {
  await login(page);
  const headers = await contractHeaders(request);
  const listing = await (await request.get("/v1/procedure_runs", { headers })).json();
  for (const row of listing.runs || []) {
    if (!row.terminal) {
      await request.post(`/v1/procedure_runs/${row.run_id}/abort`, {
        headers,
        data: { reason: "e2e reconnect cleanup leftover" },
      });
    }
  }
  await page.locator('#nav a[data-view="procedures"]').click();
  await page.locator("#proc-id").selectOption("pressure_guardrail");
  await page.locator("#proc-start").click();
  await expect(page.locator("#active-run")).toBeVisible({ timeout: 10_000 });
  const runId = await page.locator("#active-run").getAttribute("data-run");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("certarig.runId"))).toBe(runId);
  await page.reload();
  await expect(page.locator("#health-pill")).toHaveAttribute("data-state", "ok", { timeout: 15_000 });
  await page.locator('#nav a[data-view="procedures"]').click();
  await expect(page.locator("#active-run")).toHaveAttribute("data-run", runId);
  await request.post(`/v1/procedure_runs/${runId}/abort`, {
    headers: await contractHeaders(request),
    data: { reason: "e2e reconnect cleanup" },
  });
});
