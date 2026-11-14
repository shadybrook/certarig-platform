import { test, expect } from "@playwright/test";
async function signin(browser, role = "author") {
  const context = await browser.newContext();
  await context.addCookies([
    {
      name: "certarig_login",
      value: "test-browser",
      url: "http://127.0.0.1:18095",
    },
  ]);
  const page = await context.newPage();
  await page.goto("/v1/auth/callback?state=test&code=" + role);
  await expect(page.locator("#product")).toBeVisible();
  await expect(page.locator("#asset option")).not.toHaveCount(0);
  return { page, context };
}
test("Journal authentic draft, revision, evaluation, source inspection and independent review", async ({
  browser,
}, info) => {
  const { page, context } = await signin(browser);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page
    .locator("#goal")
    .fill("Check the thermal bench and explain stale source refusals.");
  await page.locator("#draft-form button").click();
  await expect(page.locator("#conversation")).toContainText("stale source");
  await expect(page.locator("#inline-proposal")).toContainText(
    "Commissioning agent",
  );
  await page.locator("#session-next").click();
  await page.locator("#connection").selectOption({ index: 0 });
  await page.locator("#agent-name").fill("Journal acceptance engineer");
  await page
    .locator("#instructions")
    .fill(
      "Inspect temperature, calibration and source freshness. Never command equipment.",
    );
  await page.locator("#agent-builder [data-close-dialog]").click();
  await page.locator("#message").fill("Retain the raw source evidence.");
  await page.locator("#message-form button").click();
  await expect(page.locator("#conversation")).toContainText(
    "Retain the raw source evidence.",
  );
  await page.locator("#commit-draft").click();
  await expect(page.locator("#notice")).toContainText("immutable version");
  const route = page.url();
  await page.reload();
  await expect(page.locator("#conversation")).toContainText(
    "Retain the raw source evidence.",
  );
  expect(page.url()).toBe(route);
  await page.locator("#evaluate").click();
  await expect(page.locator("#qualification")).toContainText(
    "awaiting_sandbox",
  );
  await page.locator("#qualify").click();
  await expect(page.locator("#qualification")).toContainText("trusted Sandbox");
  await expect(page.locator("#review")).toBeDisabled();
  await page.locator("[data-context=sources]").click();
  await expect(page.locator("#context-sources")).toContainText("fixture-only");
  await page.locator("[data-context=proposal]").click();
  await page.screenshot({
    path: info.outputPath("journal-connected-desktop.png"),
  });
  const reviewer = await signin(browser, "reviewer");
  await reviewer.page.locator("[data-route=agents]").click();
  await reviewer.page
    .locator("#versions button")
    .filter({ hasText: "Journal acceptance engineer" })
    .last()
    .click();
  await expect(reviewer.page.locator("#review")).toBeEnabled();
  await reviewer.page.locator("#review").click();
  await reviewer.page
    .getByRole("button", {
      name: "Approve exact observation proposal",
      exact: true,
    })
    .click();
  await expect(reviewer.page.locator("#notice")).toContainText("approved");
  await reviewer.page.locator("[data-route=deployments]").click();
  await reviewer.page
    .getByRole("button", { name: "Start observation", exact: true })
    .last()
    .click();
  await expect(reviewer.page.locator("#deployments")).toContainText("running");
  await reviewer.page.locator("[data-route=evidence]").click();
  await expect(reviewer.page.locator("#revoke-strip")).toContainText("running");
  await reviewer.page
    .getByRole("button", { name: "Revoke active access", exact: true })
    .last()
    .click();
  await expect(reviewer.page.locator("#notice")).toContainText("revoked");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator("#nav-toggle").click();
  await page.locator("[data-route=agents]").click();
  await page.locator("#agents-new").click();
  await expect(page.locator("#agent-builder")).toBeVisible();
  await page.screenshot({
    path: info.outputPath("journal-connected-mobile-builder.png"),
  });
  await page.keyboard.press("Escape");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
  await reviewer.context.close();
  await context.close();
});
test("Journal command navigation and literal unsafe text", async ({
  browser,
}) => {
  const { page, context } = await signin(browser);
  await page.locator("#palette-open").click();
  await page.locator("#palette-query").fill("Sandbox");
  await page
    .locator("#palette-results")
    .getByRole("button", { name: "Sandbox", exact: true })
    .click();
  await expect(page.locator("[data-view=sandbox]")).toBeVisible();
  await page.locator("[data-route=sessions]").click();
  await page.locator("#goal").fill("<img src=x onerror=alert(1)>");
  await page.locator("#draft-form button").click();
  await expect(page.locator("#conversation")).toContainText("<img");
  await expect(page.locator("#conversation img")).toHaveCount(0);
  await context.close();
});
test("Bench description retains missing facts and unfamiliar experiments stay analysis-only", async ({
  browser,
}) => {
  const { page, context } = await signin(browser);
  await page.locator("[data-route=benches]").click();
  await page.locator("#spec-title").fill("Unfamiliar electrical bench");
  await page
    .locator("#spec-form")
    .getByRole("button", { name: "Save description and assess", exact: true })
    .click();
  await expect(page.locator("#spec-report")).toContainText("missing");
  await expect(page.locator("#spec-report")).toContainText(
    "Equipment identity",
  );
  await page.locator("#spec-equipment").fill("Recorded low voltage source");
  await page.locator("#spec-transport").selectOption("serial_jsonl");
  await page.locator("#spec-linked").check();
  await page.locator("#spec-channel").fill("load_voltage");
  await page.locator("#spec-quantity").selectOption("voltage");
  await page.locator("#spec-unit").fill("V");
  await page.locator("#spec-source").fill("recorded.channel.voltage");
  await page.locator("#spec-calibration").fill("Fixture calibration reference");
  await page.locator("#spec-min").fill("0");
  await page.locator("#spec-max").fill("5");
  await page.locator("#spec-age").fill("1");
  await page.locator("#spec-gain").fill("1");
  await page.locator("#spec-offset").fill("0");
  await page.locator("#spec-sources").fill("Fixture instrument sheet page 1");
  await page.locator("#spec-save").click();
  await expect(page.locator("#spec-report")).toContainText("analysis only");
  await expect(page.locator("#spec-report")).toContainText(
    "No trusted procedure",
  );
  await page.locator("#spec-propose").click();
  await expect(page.locator("#spec-status")).toContainText("proposed");
  await page.reload();
  await page.locator("[data-route=benches]").click();
  await page
    .locator("#spec-list button")
    .filter({ hasText: "Unfamiliar electrical bench" })
    .last()
    .click();
  await expect(page.locator("#spec-title")).toHaveValue(
    "Unfamiliar electrical bench",
  );
  await expect(page.locator("#spec-report")).toContainText(
    "no execution authority",
  );
  await context.close();
});
test("Draft conflicts preserve edits and offer separate-draft recovery", async ({
  browser,
}) => {
  const { page, context } = await signin(browser);
  await page.locator("#goal").fill("Conflict recovery check");
  await page.locator("#draft-form button").click();
  await expect(page.locator("#draft-status")).toContainText("Saved");
  const id = page.url().split("/").at(-1);
  await page.evaluate(async (id) => {
    const me = await (await fetch("/v1/auth/me")).json();
    const d = await (await fetch("/v1/drafts/" + id)).json();
    await fetch("/v1/drafts/" + id, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": me.csrf },
      body: JSON.stringify({
        expected_revision: d.revision,
        message: "Remote edit must remain",
      }),
    });
  }, id);
  await page.locator("#session-next").click();
  await page.locator("#instructions").fill("Local edit must remain");
  await page.locator("#agent-builder [data-close-dialog]").click();
  await page.locator("#persist-draft").click();
  await expect(
    page.getByRole("dialog", { name: "Resolve draft conflict" }),
  ).toBeVisible();
  await expect(
    page.getByRole("dialog", { name: "Resolve draft conflict" }),
  ).toContainText("Local edit must remain");
  await expect(
    page.getByRole("dialog", { name: "Resolve draft conflict" }),
  ).toContainText("Remote edit must remain");
  await page
    .getByRole("button", { name: "Save local as a new draft", exact: true })
    .click();
  await expect(page.locator("#notice")).toContainText("separate draft");
  expect(page.url()).not.toContain(id);
  await context.close();
});
test("Advanced authoring saves a resumable draft with original version lineage", async ({
  browser,
}) => {
  const { page, context } = await signin(browser);
  await page.locator("#session-next").click();
  await page.locator("#agent-name").fill("Advanced lineage sample");
  await page
    .locator("#instructions")
    .fill("Baseline for this independent advanced-authoring test.");
  await page.locator("#save-agent").click();
  await expect(page.locator("#notice")).toContainText(
    "Saved immutable version",
  );
  await page.locator("#session-next").click();
  await page
    .locator("#instructions")
    .fill("Advanced resumable instructions with exact source checks.");
  await page.locator("#save-advanced-draft").click();
  await expect(page.locator("#notice")).toContainText("resumable draft");
  const draftRoute = page.url();
  await page.locator("#agent-builder [data-close-dialog]").click();
  await page.reload();
  await expect(page.locator("#conversation")).toContainText(
    "Advanced resumable instructions",
  );
  expect(page.url()).toBe(draftRoute);
  await page.locator("#commit-draft").click();
  await expect(page.locator("#notice")).toContainText("immutable version");
  await context.close();
});
test("Journal evaluated team uses exact members and receives independent team review", async ({
  browser,
}) => {
  const { page, context } = await signin(browser);
  await page.locator("#session-next").click();
  await page.locator("#agent-name").fill("Journal team specialist");
  await page
    .locator("#instructions")
    .fill("Inspect source quality without equipment commands.");
  await page.locator("#save-agent").click();
  await expect(page.locator("#notice")).toContainText("Saved immutable");
  await page.locator("#evaluate").click();
  await expect(page.locator("#qualification")).toContainText(
    "awaiting_sandbox",
  );
  await page.locator("#qualify").click();
  await expect(page.locator("#qualification")).toContainText("trusted Sandbox");
  await page.locator("[data-route=agents]").click();
  await page.locator("#team-name").fill("Journal supervised commissioning");
  const supervisors = await page
    .locator("#supervisor option")
    .evaluateAll((nodes) =>
      nodes
        .filter((n) => !n.disabled)
        .map((n) => ({ value: n.value, label: n.textContent })),
    );
  await page
    .locator("#supervisor")
    .selectOption(
      supervisors.find((o) => o.label.includes("Journal acceptance engineer"))
        .value,
    );
  await expect(
    page
      .locator("#specialists option:not(:disabled)")
      .filter({ hasText: "Journal team specialist" }),
  ).toHaveCount(1);
  const options = await page
    .locator("#specialists option")
    .evaluateAll((nodes) =>
      nodes
        .filter((n) => !n.disabled)
        .map((n) => ({ value: n.value, label: n.textContent })),
    );
  await page
    .locator("#specialists")
    .selectOption(
      options.find((o) => o.label.includes("Journal team specialist")).value,
    );
  await page.locator("#team-form button").click();
  await expect(page.locator("#notice")).toContainText("Team version saved");
  await page.locator("[data-route=sessions]").click();
  await page.locator("#evaluate").click();
  await expect(page.locator("#qualification")).toContainText(
    "awaiting_sandbox",
  );
  await page.locator("#qualify").click();
  await expect(page.locator("#qualification")).toContainText("trusted Sandbox");
  await page.locator("#session-next").click();
  await expect(
    page.getByRole("dialog", { name: "Inspect exact team" }),
  ).toContainText("Journal team specialist");
  await page.getByRole("button", { name: "Close team inspection" }).click();
  const reviewer = await signin(browser, "reviewer");
  await reviewer.page.locator("[data-route=agents]").click();
  await reviewer.page
    .locator("#versions button")
    .filter({ hasText: "Journal supervised commissioning" })
    .last()
    .click();
  await reviewer.page.locator("#review").click();
  await reviewer.page
    .getByRole("button", { name: "Approve exact observation proposal" })
    .click();
  await expect(reviewer.page.locator("#notice")).toContainText("approved");
  await reviewer.page.locator("[data-route=deployments]").click();
  await reviewer.page
    .getByRole("button", { name: "Revoke access", exact: true })
    .last()
    .click();
  await expect(reviewer.page.locator("#notice")).toContainText("revoked");
  await reviewer.context.close();
  await context.close();
});
