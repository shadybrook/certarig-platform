/* Deliberately isolated prototype state. No fetch, credentials or equipment APIs. */
import { element as el } from "./journal.mjs";
const $ = (id) => document.getElementById(id);
export function init(journal) {
  $("login").hidden = true;
  $("product").hidden = false;
  $("identity").textContent = "CertaRig Lab · fixture author";
  $("scope").textContent = "Two simulated benches · fixture data";
  $("signout").hidden = true;
  for (const [id, rows] of [
    [
      "asset",
      [
        ["thermal", "Thermal bench · Simulator"],
        ["pressure", "Pressure / flow · Simulator"],
      ],
    ],
    ["project", [["lab", "Commissioning laboratory"]]],
    ["connection", [["fixture", "Deterministic fixture · offline"]]],
  ]) {
    $(id).replaceChildren(
      ...rows.map(([v, t]) => {
        const o = el("option", t);
        o.value = v;
        return o;
      }),
    );
  }
  $("asset-state").textContent =
    "Reviewed simulator profile · observation only";
  $("enrollment").hidden = true;
  $("profile-review-panel").hidden = true;
  $("model-login").disabled = true;
  $("model-status").disabled = true;
  const toolbar = el("div", undefined, "fixture-controls");
  toolbar.innerHTML =
    '<strong>DESIGN PROTOTYPE</strong><label for="fixture-role">Identity</label><select id="fixture-role"><option value="author">Author</option><option value="reviewer">Independent reviewer</option></select><label for="fixture-scenario">Source state</label><select id="fixture-scenario"><option value="nominal">Nominal</option><option value="stale">Stale signal</option><option value="units">Incompatible units</option><option value="empty">No permitted bench</option><option value="no_project">No projects</option><option value="no_model">No model connection</option></select><span>Deterministic fixtures · no live authority</span>';
  $("global-status").prepend(toolbar);
  let saved;
  try {
    saved = JSON.parse(
      sessionStorage.getItem("certarig-journal-prototype") || "null",
    );
  } catch {}
  let pendingEvaluation = null;
  const data = saved || {
    revision: 1,
    committed: false,
    evaluated: false,
    qualified: false,
    reviewed: false,
    running: false,
    revoked: false,
    name: "Thermal commissioning engineer",
    instructions:
      "Inspect temperature identity, calibration and freshness. Explain readiness using recorded observations. Observe only.",
    messages: [
      {
        role: "user",
        text: "Commission the thermal bench. Verify the temperature signal and explain anything that blocks readiness.",
      },
      {
        role: "assistant",
        text: "I will inspect the mapped temperature source, its units and its calibration record. The proposed agent has observation tools only. Review the definition below before evaluation.",
      },
    ],
  };
  $("agent-name").value = data.name;
  $("instructions").value = data.instructions;
  $("tool-options").replaceChildren(
    ...["Read signals", "Read state", "Read configuration"].map((name, i) => {
      const label = el("label", undefined, "check");
      const input = el("input");
      input.type = "checkbox";
      input.name = "tools";
      input.value = ["read_signals", "read_state", "read_rig"][i];
      input.checked = true;
      label.append(input, document.createTextNode(name));
      return label;
    }),
  );
  $("analysis-permissions").textContent =
    "No independently reviewed analysis tool on this fixture bench.";
  $("analysis-source").value =
    "import json\nfrom pathlib import Path\nsamples = [22.1, 22.4, 22.8]\nPath('result.json').write_text(json.dumps({'mean_degC':sum(samples)/len(samples)}))";
  const persist = () =>
    sessionStorage.setItem("certarig-journal-prototype", JSON.stringify(data));
  const notice = (s, error = false) => {
    $("notice").textContent = s;
    $("notice").dataset.error = String(error);
  };
  const b = (s, fn) => {
    const n = el("button", s);
    n.type = "button";
    n.onclick = fn;
    return n;
  };
  function render() {
    persist();
    const scenario = $("fixture-scenario").value;
    const blocked = ["stale", "units", "empty", "no_model"].includes(scenario);
    if (scenario === "empty") {
      $("asset").replaceChildren(el("option", "No permitted bench"));
      $("asset").firstChild.value = "";
    } else if (!$("asset").value) {
      for (const [v, t] of [
        ["thermal", "Thermal bench · Simulator"],
        ["pressure", "Pressure / flow · Simulator"],
      ]) {
        const o = el("option", t);
        o.value = v;
        $("asset").append(o);
      }
      $("asset").value = "thermal";
    }
    $("project").disabled = scenario === "no_project";
    $("connection").disabled = scenario === "no_model";
    const reviewer = $("fixture-role").value === "reviewer";
    $("agent-form")
      .querySelectorAll("input,select,textarea,button")
      .forEach((n) => (n.disabled = reviewer));
    $("connection").disabled = reviewer || scenario === "no_model";
    $("project").firstChild.textContent =
      scenario === "no_project"
        ? "No projects yet"
        : "Commissioning laboratory";
    $("project").firstChild.value = scenario === "no_project" ? "" : "lab";
    $("connection").firstChild.textContent =
      scenario === "no_model"
        ? "No model connection"
        : "Deterministic fixture · offline";
    $("connection").firstChild.value = scenario === "no_model" ? "" : "fixture";
    $("draft-form").hidden = Boolean(data.messages.length);
    $("message-form").hidden = reviewer;
    $("persist-draft").disabled = reviewer;
    $("commit-draft").disabled =
      reviewer || data.committed || ["empty", "no_model"].includes(scenario);
    $("conversation").replaceChildren(
      ...data.messages.map((m) => {
        const a = el("article", undefined, "conversation-message");
        a.append(
          el(
            "strong",
            m.role === "user"
              ? "You"
              : "Commissioning assistant · deterministic fixture",
          ),
          el("p", m.text),
        );
        return a;
      }),
    );
    $("draft-status").textContent =
      `Saved · revision ${data.revision} · ${data.committed ? "committed" : "draft"}`;
    $("version-label").textContent = data.committed
      ? `Version ${data.revision} · fixture only`
      : `Draft · revision ${data.revision}`;
    $("draft-blockers").textContent = blocked
      ? $("fixture-scenario").value === "stale"
        ? "Temperature source is stale. Restore acquisition and repeat evaluation."
        : $("fixture-scenario").value === "no_model"
          ? "No model connection. Create an authorized connection before evaluation."
          : $("fixture-scenario").value === "empty"
            ? "No permitted bench. An operator must enroll an asset and a Reviewer must grant access."
            : "Temperature quantity received pressure units. Correct the reviewed mapping before evaluation."
      : "";
    $("draft-diff").textContent = JSON.stringify([
      { field: "instructions", after: data.instructions },
      { field: "tools", after: ["read_signals", "read_state", "read_rig"] },
    ]);
    $("draft-list").replaceChildren(
      b("Thermal readiness · saved session", () => {
        location.hash = "/sessions";
      }),
    );
    $("versions").replaceChildren(
      b(
        `${data.name} · ${data.committed ? "v" + data.revision : "draft"}`,
        () => {
          location.hash = "/sessions";
          journal.openBuilder();
        },
      ),
    );
    $("evaluate").disabled =
      !data.committed ||
      reviewer ||
      Boolean(pendingEvaluation) ||
      ["empty", "no_model"].includes(scenario);
    $("qualify").disabled = !data.evaluated || blocked || reviewer;
    $("review").disabled = !data.qualified || !reviewer || blocked;
    $("qualification").textContent = data.qualified
      ? "Fixture rehearsal passed · not genuine container qualification"
      : data.evaluated
        ? blocked
          ? "Fixture evaluation blocked · repair the source first"
          : "Fixture evaluation matched · rehearsal required"
        : "Save a version, then evaluate the selected profile.";
    if (data.evaluated)
      $("qualification").textContent += blocked
        ? " · Readiness blocked: stale or incompatible source."
        : " · Fixture readiness: identity, units, calibration reference and freshness matched.";
    $("definition").textContent = JSON.stringify(
      {
        name: data.name,
        profile: "thermal-fixture-v1",
        tools: ["read_signals", "read_state", "read_rig"],
        instructions: data.instructions,
        limits: {
          model_calls: 8,
          max_assessments: 10,
          interval_s: 30,
          lease_s: 900,
        },
        evaluation: data.evaluated
          ? {
              status: blocked ? "blocked" : "ready",
              reason: blocked
                ? "Source freshness or unit checks failed. Restore acquisition or correct mapping, then repeat evaluation."
                : "Fixture identity, degC units, CAL-T-01 calibration reference and 0.2 s age matched this simulated profile.",
              trace: [
                {
                  tool: "read_signals",
                  channel_id: "temperature",
                  value: 22.8,
                  unit: "degC",
                  source_age_s: 0.2,
                  calibration: "CAL-T-01",
                },
              ],
            }
          : null,
        rehearsal: data.qualified
          ? "fixture only - not runtime qualification"
          : "not recorded",
        mode: "observation",
        fixture: true,
      },
      null,
      2,
    );
    $("review-blocker").textContent = reviewer
      ? "Review the exact version and its fixture evidence."
      : "The author cannot independently review their own version.";
    const rows = data.running
      ? [["temperature", "22.8", "degC", "0.2 s", "good"]]
      : [
          [
            "temperature",
            "22.8",
            "degC",
            blocked ? "8.4 s" : "0.2 s",
            blocked ? "blocked" : "good",
          ],
        ];
    const table = el("div", undefined, "table-wrap");
    table.innerHTML =
      '<table class="data-table"><thead><tr><th>Signal</th><th>Value</th><th>Unit</th><th>Age</th><th>Quality</th></tr></thead><tbody></tbody></table>';
    for (const row of rows) {
      const tr = el("tr");
      tr.append(...row.map((v) => el("td", v)));
      table.querySelector("tbody").append(tr);
    }
    $("bench-observations").replaceChildren(
      el("h2", "Observed channels"),
      el("p", "Simulator snapshot · fixture calibration record CAL-T-01"),
      table,
    );
    $("context-sources").replaceChildren(
      el("h2", "Recorded observations"),
      el(
        "p",
        `Temperature: 22.8 ${$("fixture-scenario").value === "units" ? "bar (incompatible)" : "degC"} · age ${blocked ? "8.4 s (stale)" : "0.2 s"} · fixture calibration CAL-T-01`,
      ),
      el(
        "p",
        "Fixture profile thermal-v1 · simulation only. Raw observations remain distinct from readiness claims.",
      ),
    );
    if (scenario === "empty") {
      $("bench-observations").replaceChildren(el("h2", "No permitted source"));
      $("context-sources").replaceChildren(
        el("p", "No permitted source. A Reviewer must grant bench access."),
      );
    }
    $("deployments").replaceChildren();
    $("runtime-health").textContent = "Fixture observation runtime · simulated";
    if (data.reviewed) {
      const row = el("article", undefined, "deployment");
      row.append(
        el(
          "h3",
          data.revoked
            ? "Access revoked"
            : data.running
              ? "Observation running"
              : "Reviewed fixture proposal",
        ),
        el("p", "Fixture lease · 15 minute maximum · no equipment authority"),
      );
      if (!data.running && !data.revoked)
        row.append(
          b("Start observation", () => {
            data.running = true;
            notice("Fixture observation started.");
            render();
          }),
        );
      if (!data.revoked)
        row.append(
          b("Revoke access", () => {
            data.running = false;
            data.revoked = true;
            notice("Access revoked. Late fixture results are discarded.");
            render();
          }),
        );
      $("deployments").append(row);
    }
    let strip = $("revoke-strip");
    if (!strip) {
      strip = el("div");
      strip.id = "revoke-strip";
      $("global-status").append(strip);
    }
    strip.replaceChildren();
    if (data.running)
      strip.append(
        el("p", "Running · observation only · fixture lease"),
        b("Revoke active access", () => {
          data.running = false;
          data.revoked = true;
          notice("Access revoked.");
          render();
        }),
      );
    $("evidence-list").replaceChildren(
      el(
        "h3",
        data.evaluated
          ? "Thermal evaluation · fixture evidence"
          : "No exported run yet",
      ),
      el(
        "p",
        "Deterministic prototype records do not qualify the real runtime.",
      ),
    );
    if (data.evaluated)
      $("evidence-list").append(
        b("Inspect raw evidence", () => {
          $("evidence-list").append(
            el(
              "pre",
              JSON.stringify(
                {
                  fixture: true,
                  samples: [22.1, 22.4, 22.8],
                  unit: "degC",
                  blocked,
                  version: data.revision,
                },
                null,
                2,
              ),
            ),
          );
        }),
        b("Export prototype evidence", () => {
          const a = el("a");
          a.href = URL.createObjectURL(
            new Blob([JSON.stringify({ ...data, fixture: true }, null, 2)], {
              type: "application/json",
            }),
          );
          a.download = "certarig-prototype-evidence.json";
          a.click();
          URL.revokeObjectURL(a.href);
          notice(
            "Prototype JSON exported. It is not a verified production bundle.",
          );
        }),
      );
    journal.update();
  }
  $("agent-form").onsubmit = (e) => {
    e.preventDefault();
    data.name = $("agent-name").value;
    data.instructions = $("instructions").value;
    data.revision++;
    data.committed = true;
    data.evaluated = false;
    data.qualified = false;
    data.reviewed = false;
    $("agent-builder").close();
    notice("Fixture immutable version saved.");
    render();
  };
  $("message-form").onsubmit = (e) => {
    e.preventDefault();
    data.messages.push(
      { role: "user", text: $("message").value },
      {
        role: "assistant",
        text: "Requirement added to the fixture proposal. Inspect the revised definition before evaluation.",
      },
    );
    data.instructions += "\n" + $("message").value;
    data.revision++;
    data.committed = false;
    data.evaluated = false;
    data.qualified = false;
    $("instructions").value = data.instructions;
    $("message").value = "";
    render();
  };
  $("persist-draft").onclick = () => {
    data.name = $("agent-name").value;
    data.instructions = $("instructions").value;
    notice("Fixture draft saved.");
    render();
  };
  $("commit-draft").onclick = () => {
    data.committed = true;
    notice("Fixture version committed.");
    render();
  };
  $("evaluate").onclick = () => {
    data.evaluated = false;
    data.qualified = false;
    const job = Symbol("fixture-evaluation");
    pendingEvaluation = job;
    const cancel = b("Cancel task", () => {
      pendingEvaluation = null;
      $("task-list").replaceChildren(
        el("h3", "Fixture evaluation · cancelled"),
      );
      notice("Fixture task cancelled. Late results discarded.");
      render();
    });
    $("task-list").replaceChildren(
      el("h3", "Fixture evaluation · running"),
      cancel,
    );
    notice("Fixture evaluation running.");
    render();
    setTimeout(() => {
      if (pendingEvaluation !== job) return;
      pendingEvaluation = null;
      data.evaluated = true;
      $("task-list").replaceChildren(
        el("h3", "Fixture evaluation · completed"),
        el(
          "p",
          $("fixture-scenario").value === "nominal"
            ? "Nominal fixture readiness matched identity, units, freshness and calibration reference."
            : "Refusal matched. Repair source data before qualification.",
        ),
      );
      notice("Fixture evaluation completed.");
      render();
    }, 650);
  };
  $("qualify").onclick = () => {
    data.qualified = true;
    notice(
      "Fixture rehearsal passed. Real Sandbox qualification remains unverified.",
    );
    render();
  };
  $("review").onclick = () => {
    data.reviewed = true;
    data.revoked = false;
    notice(
      "Independent fixture review recorded. Start observation separately.",
    );
    location.hash = "/deployments";
    render();
  };
  $("fixture-role").onchange = render;
  $("fixture-scenario").onchange = () => {
    pendingEvaluation = null;
    data.evaluated = false;
    data.qualified = false;
    data.reviewed = false;
    data.running = false;
    render();
  };
  $("new-agent").onclick = () => {
    data.committed = false;
    $("goal").value = "";
    $("draft-form").hidden = false;
  };
  $("draft-form").onsubmit = (e) => {
    e.preventDefault();
    data.messages = [{ role: "user", text: $("goal").value }];
    data.name = "Commissioning agent";
    data.instructions = $("goal").value;
    $("instructions").value = data.instructions;
    $("agent-name").value = data.name;
    data.committed = false;
    render();
  };
  $("analysis-form").onsubmit = (e) => {
    e.preventDefault();
    $("analysis-tools").replaceChildren(
      el("h3", $("analysis-name").value || "Temperature analysis"),
      el("p", "Fixture tool · source saved"),
      b("Run declared tests", () => {
        $("analysis-runs").replaceChildren(
          el("h3", "Fixture experiment · completed"),
          el("pre", '{"mean_degC":22.4333333333}'),
          el("p", "Fixture analysis only. No trusted receipt issued."),
        );
        notice("Fixture analysis completed.");
      }),
    );
    notice("Fixture tool source saved.");
  };
  $("connector-profile-form").onsubmit = (e) => {
    e.preventDefault();
    $("connector-profiles").replaceChildren(
      el("h3", $("connector-profile-name").value),
      el("p", "Proposed mapping · operator installation required"),
      el("pre", $("connector-channels").value),
    );
  };
  $("replay-form").onsubmit = (e) => {
    e.preventDefault();
    $("replay-list").append(
      el("p", $("replay-name").value + " · unverified user import"),
    );
  };
  $("team-form").onsubmit = (e) => {
    e.preventDefault();
    notice(
      "Select exact evaluated specialist versions. This fixture has only one agent.",
      true,
    );
  };
  for (const id of ["supervisor", "specialists"]) {
    $(id).replaceChildren(el("option", data.name + " · v1"));
  }
  $("refresh").onclick = () => {
    notice("Fixture state refreshed.");
    render();
  };
  $("project-form").onsubmit = (e) => {
    e.preventDefault();
    notice("Fixture project saved. Bench permissions stay separate.");
  };
  $("model-form").onsubmit = (e) => {
    e.preventDefault();
    notice("Prototype mode uses its isolated deterministic connection.");
  };
  $("model-disconnect").onclick = () =>
    notice("Fixture connection disconnected. No live provider was contacted.");
  render();
}
