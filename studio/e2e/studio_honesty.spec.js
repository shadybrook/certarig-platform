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

test("commissioning facts from one description propose and apply a trip", async ({ page, request }) => {
  await login(page);
  await page.locator('#nav a[data-view="onboard"]').click();
  await page.getByTestId("interview-start").click();
  await expect(page.getByTestId("interview-needs")).toContainText("modules");
  await page.getByTestId("interview-text").fill(
    "ADC pots, E-stop, relay. pressure 4.05 bar, flow 14.5 L/min. observe-only: none. sim-stranger.md"
  );
  await page.getByTestId("interview-record").click();
  await expect(page.getByTestId("interview-prompt")).toContainText("Required facts are in");
  await page.getByTestId("interview-propose").click();
  await expect(page.getByTestId("interview-diff")).toContainText("next");
  await page.getByTestId("interview-apply").click();
  const rig = await (await request.get("/v1/rig", { headers: { "X-CertaRig-Operator-Key": OPERATOR } })).json();
  expect(rig.rig.abort_limits.pressure).toBe(4.05);
});

test("onboard can add a channel and preview without apply", async ({ page }) => {
  await login(page);
  await page.locator('#nav a[data-view="onboard"]').click();
  await page.getByTestId("onboard-add").click();
  await page.locator("#onboard-propose").click();
  await expect(page.getByTestId("onboard-diff")).toContainText("channels");
});

test("trigger coach shows which pot to move", async ({ page, request }) => {
  await login(page);
  const headers = await contractHeaders(request);
  const listing = await (await request.get("/v1/procedure_runs", { headers })).json();
  for (const row of listing.runs || []) {
    if (!row.terminal) {
      await request.post(`/v1/procedure_runs/${row.run_id}/abort`, {
        headers,
        data: { reason: "e2e trigger cleanup leftover" },
      });
    }
  }
  await page.locator('#nav a[data-view="procedures"]').click();
  await page.locator("#proc-id").selectOption("adc_validation");
  await page.locator("#proc-start").click();
  await expect(page.getByTestId("trigger-coach")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("trigger-coach")).toContainText("P1");
  const runId = await page.locator("#active-run").getAttribute("data-run");
  await request.post(`/v1/procedure_runs/${runId}/abort`, {
    headers: await contractHeaders(request),
    data: { reason: "e2e trigger cleanup" },
  });
});

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
  const started = await (
    await request.post("/v1/procedure_runs", {
      headers,
      data: { procedure_id: "pressure_guardrail" },
    })
  ).json();
  const runId = started.run_id;
  await page.evaluate((id) => localStorage.setItem("certarig.runId", id), runId);
  await page.locator('#nav a[data-view="procedures"]').click();
  await expect(page.locator("#active-run")).toHaveAttribute("data-run", runId);
  await page.reload();
  await expect(page.locator("#health-pill")).toHaveAttribute("data-state", "ok", { timeout: 15_000 });
  await expect.poll(() => page.evaluate(() => localStorage.getItem("certarig.runId"))).toBe(runId);
  await page.locator('#nav a[data-view="procedures"]').click();
  await expect(page.locator("#active-run")).toHaveAttribute("data-run", runId);
  await request.post(`/v1/procedure_runs/${runId}/abort`, {
    headers: await contractHeaders(request),
    data: { reason: "e2e reconnect cleanup" },
  });
});
