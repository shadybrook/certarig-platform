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

async function setPressure(page, request, value) {
  await page.locator('#nav a[data-view="telemetry"]').click();
  const slider = page.getByTestId("sim-pressure_emulator");
  await expect(slider).toBeVisible();
  await slider.evaluate((el, v) => {
    el.value = String(v);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, value);
  await request.post("/v1/sim/set_target", {
    headers: await contractHeaders(request),
    data: { channel: "pressure_emulator", value },
  });
}

async function currentStep(request) {
  const body = await (
    await request.get("/v1/procedure_runs", { headers: { "X-CertaRig-Operator-Key": OPERATOR } })
  ).json();
  const run = (body.runs || [])[0];
  return run ? { status: run.status, step: run.current_step, terminal: run.terminal } : {};
}

test("pressure_guardrail trips from Studio and then passes after the operator lowers pressure", async ({
  page,
  request,
}) => {
  await login(page);
  await page.locator('#nav a[data-view="procedures"]').click();
  await page.locator("#proc-id").selectOption("pressure_guardrail");
  await page.locator("#proc-start").click();
  await expect(page.locator("#active-run")).toBeVisible({ timeout: 10_000 });

  await expect
    .poll(async () => (await currentStep(request)).step, { timeout: 15_000 })
    .toBe("raise_pressure");
  await setPressure(page, request, 5.2);
  await expect
    .poll(async () => (await currentStep(request)).step, { timeout: 15_000 })
    .toBe("lower_pressure");

  await page.locator('#nav a[data-view="procedures"]').click();
  await expect(page.locator('[data-step="raise_pressure"]')).toHaveAttribute("data-status", "passed");

  await setPressure(page, request, 2.0);
  await expect
    .poll(async () => (await currentStep(request)).status, { timeout: 20_000 })
    .toBe("passed");

  await page.locator('#nav a[data-view="procedures"]').click();
  await expect(page.locator("#run-status")).toHaveText("passed");
});

test("operator can grant an approval from the inbox", async ({ page, request }) => {
  await login(page);
  await request.post("/v1/approvals/request", {
    headers: {
      "X-CertaRig-Agent-Key": "sim-agent-key-0000000001",
      "X-CertaRig-Contract": (await (await request.get("/v1/rig")).json()).contract_hash,
    },
    data: { tool: "reset_trip", args: {}, reason: "e2e inbox" },
  });
  await page.locator('#nav a[data-view="approvals"]').click();
  await expect(page.locator("[data-approval]")).toBeVisible();
  await page.getByRole("button", { name: "Grant" }).click();
  await expect(page.getByText("granted")).toBeVisible({ timeout: 10_000 });
});
