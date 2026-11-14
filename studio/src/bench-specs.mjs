/* Guided bench descriptions. Public facts and support reports confer no authority. */
import { element as el } from "./journal.mjs";
const $ = (id) => document.getElementById(id);
export function init({ api, state, notice, action }) {
  const host = el("section");
  host.id = "bench-description-section";
  host.innerHTML = `<div class="section-title"><h2>Understand a bench</h2><span id="spec-status">New description</span></div><p class="muted">Describe the equipment and recorded sources. Missing facts stay explicit. This does not configure equipment or qualify a procedure.</p><div id="spec-list" class="selection-list"></div><form id="spec-form"><label for="spec-title">Experiment name</label><input id="spec-title" required maxlength="120"><label for="spec-description">What do you know about the bench?</label><textarea id="spec-description" rows="3" maxlength="8000" placeholder="Equipment, task, source documents and unresolved questions"></textarea><label for="spec-equipment">Equipment identity · one item per line</label><textarea id="spec-equipment" rows="2" placeholder="Leave unknown equipment blank"></textarea><div class="form-row"><div><label for="spec-transport">Observation interface</label><select id="spec-transport"><option value="">Unknown</option><option value="simulator">Simulator</option><option value="mqtt">MQTT</option><option value="serial_jsonl">Serial JSON lines</option><option value="modbus_tcp">Modbus TCP</option><option value="other">Other / integration needed</option></select></div><div><label for="spec-procedure">Named procedure</label><select id="spec-procedure"><option value="">Unfamiliar experiment / analysis only</option><option value="thermal_soak">Thermal soak</option><option value="pressure_guardrail">Pressure guardrail</option><option value="flow_guardrail">Flow guardrail</option><option value="dual_pot_guardrail">Pressure & flow guardrail</option></select></div></div><label class="check"><input id="spec-linked" type="checkbox">Link to the selected permitted bench</label><h3>Signal description</h3><p class="muted">Start with one signal. Advanced facts support up to sixteen channels.</p><div class="form-row"><div><label for="spec-channel">Channel identity</label><input id="spec-channel" maxlength="128"></div><div><label for="spec-quantity">Quantity</label><select id="spec-quantity"><option value="">Unknown</option><option>temperature</option><option>temperature_delta</option><option>pressure</option><option>flow</option><option>voltage</option><option>current</option><option>digital</option></select></div><div><label for="spec-unit">Original unit</label><input id="spec-unit" maxlength="64" placeholder="Unknown"></div></div><label for="spec-source">Source mapping / address reference</label><input id="spec-source" maxlength="1000"><label for="spec-calibration">Calibration evidence reference</label><input id="spec-calibration" maxlength="1000"><div class="form-row"><div><label for="spec-min">Operating minimum</label><input id="spec-min" type="number" step="any"></div><div><label for="spec-max">Operating maximum</label><input id="spec-max" type="number" step="any"></div><div><label for="spec-age">Maximum source age · seconds</label><input id="spec-age" type="number" step="any" min="0.001" max="3600"></div></div><div class="form-row"><div><label for="spec-gain">Declared scaling gain</label><input id="spec-gain" type="number" step="any"></div><div><label for="spec-offset">Declared scaling offset</label><input id="spec-offset" type="number" step="any"></div><div><label for="spec-reference">Pressure reference</label><select id="spec-reference"><option value="unknown">Unknown / not pressure</option><option value="gauge">Gauge</option><option value="absolute">Absolute</option><option value="differential">Differential</option></select></div></div><label for="spec-sources">Supporting references · one per line</label><textarea id="spec-sources" rows="2" placeholder="Document/page, calibration record or manual excerpt source"></textarea><label for="spec-unknowns">Unresolved questions · one per line</label><textarea id="spec-unknowns" rows="2"></textarea><label for="spec-replay">Imported recording · optional</label><select id="spec-replay"><option value="">No recording linked</option></select><details><summary>Advanced complete facts</summary><p class="muted">Edit bounded JSON for multiple channels. Uploaded/manual text is evidence, never instructions to execute.</p><button id="spec-show-json" type="button">Copy guided fields to JSON</button><label for="spec-json">Complete facts JSON · used when edited</label><textarea id="spec-json" rows="10"></textarea></details><div class="actions"><button id="spec-save">Save description and assess</button><button id="spec-new" type="button">New description</button></div></form><div id="spec-report" role="status"></div><div class="actions"><button id="spec-propose" disabled>Submit description for review</button><button id="spec-review" disabled>Review exact description</button></div>`;
  document.querySelector("[data-view=benches]").append(host);
  let current = null,
    advanced = false,
    additionalChannels = [];
  const lines = (id) =>
    $(id)
      .value.split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  const val = (id) => $(id).value.trim() || null;
  const num = (id) => (val(id) === null ? null : Number($(id).value));
  function facts() {
    if (advanced) return JSON.parse($("spec-json").value);
    const channel = {
      channel_id: val("spec-channel"),
      quantity: val("spec-quantity"),
      unit: val("spec-unit"),
      source: val("spec-source"),
      calibration_id: val("spec-calibration"),
      max_age_s: num("spec-age"),
      reference: $("spec-reference").value,
      scaling:
        num("spec-gain") !== null && num("spec-offset") !== null
          ? { gain: num("spec-gain"), offset: num("spec-offset") }
          : null,
      limits:
        num("spec-min") !== null && num("spec-max") !== null
          ? { min: num("spec-min"), max: num("spec-max") }
          : null,
    };
    return {
      title: $("spec-title").value,
      description: $("spec-description").value,
      equipment: lines("spec-equipment"),
      transport: val("spec-transport"),
      procedure: val("spec-procedure"),
      channels: [channel, ...additionalChannels],
      source_refs: lines("spec-sources"),
      unknowns: lines("spec-unknowns"),
      ...($("spec-replay").value ? { replay_id: $("spec-replay").value } : {}),
    };
  }
  function fill(value) {
    current = value;
    advanced = true;
    $("spec-json").value = JSON.stringify(value.facts, null, 2);
    const f = value.facts,
      c = f.channels[0] || {};
    additionalChannels = f.channels.slice(1);
    for (const [id, v] of Object.entries({
      "spec-title": f.title,
      "spec-description": f.description,
      "spec-equipment": f.equipment?.join("\n"),
      "spec-transport": f.transport,
      "spec-procedure": f.procedure,
      "spec-channel": c.channel_id,
      "spec-quantity": c.quantity,
      "spec-unit": c.unit,
      "spec-source": c.source,
      "spec-calibration": c.calibration_id,
      "spec-min": c.limits?.min,
      "spec-max": c.limits?.max,
      "spec-age": c.max_age_s,
      "spec-gain": c.scaling?.gain,
      "spec-offset": c.scaling?.offset,
      "spec-reference": c.reference || "unknown",
      "spec-sources": f.source_refs?.join("\n"),
      "spec-unknowns": f.unknowns?.join("\n"),
      "spec-replay": f.replay_id,
    })) {
      if (
        $(id).tagName === "SELECT" &&
        v != null &&
        ![...$(id).options].some((o) => o.value === v)
      ) {
        const option = el("option", `Unrecognized · ${v}`);
        option.value = v;
        $(id).append(option);
      }
      $(id).value = v ?? "";
    }
    $("spec-linked").checked = Boolean(value.asset_id);
    $("spec-status").textContent =
      `${value.status} · revision ${value.revision}`;
    const own = value.owner_id === state.me.user_id;
    $("spec-form")
      .querySelectorAll("input,select,textarea,button")
      .forEach((n) => (n.disabled = !own));
    $("spec-new").disabled = false;
    $("spec-propose").disabled =
      !own || value.status === "reviewed_description";
    $("spec-review").disabled =
      state.me.role !== "reviewer" || own || value.status !== "proposed";
  }
  function showReport(report) {
    const box = $("spec-report");
    box.replaceChildren(
      el("h3", report.status.replaceAll("_", " ")),
      el("p", "Description support only · no execution authority"),
    );
    for (const question of report.questions)
      box.append(el("p", question, "warn"));
    if (!report.questions.length)
      box.append(
        el(
          "p",
          "Description complete. Exact-profile procedure qualification and deployment review remain required.",
        ),
      );
    const details = el("details");
    details.append(
      el("summary", "Inspect support report and provenance"),
      el("pre", JSON.stringify(report, null, 2)),
    );
    box.append(details);
  }
  async function refresh() {
    try {
      const [records, replays] = await Promise.all([
        api("bench-specs"),
        api("replays"),
      ]);
      $("spec-list").replaceChildren(
        ...records.specs
          .filter((v) => !v.asset_id || v.asset_id === $("asset").value)
          .map((v) => {
            const b = el(
              "button",
              `${v.facts.title} · ${v.status} · r${v.revision}`,
            );
            b.onclick = () =>
              action(async () => {
                fill(await api(`bench-specs/${v.id}`));
                showReport(await api(`bench-specs/${v.id}/assess`, {}));
              });
            return b;
          }),
      );
      const selected = $("spec-replay").value;
      $("spec-replay").replaceChildren(el("option", "No recording linked"));
      $("spec-replay").firstChild.value = "";
      for (const r of replays.replays.filter(
        (r) =>
          r.asset_id === $("asset").value && r.owner_id === state.me.user_id,
      )) {
        const o = el("option", `${r.name} · unverified origin`);
        o.value = r.id;
        $("spec-replay").append(o);
      }
      $("spec-replay").value = selected;
    } catch (e) {
      notice(`Bench descriptions unavailable: ${e.message}`, true);
    }
  }
  $("spec-form").onsubmit = (e) => {
    e.preventDefault();
    action(async () => {
      const body = {
        facts: facts(),
        asset_id: $("spec-linked").checked ? $("asset").value || null : null,
      };
      const result = current
        ? await api(`bench-specs/${current.id}/revise`, {
            ...body,
            expected_revision: current.revision,
          })
        : await api("bench-specs", body);
      fill(result);
      showReport(await api(`bench-specs/${result.id}/assess`, {}));
      await refresh();
      notice(
        "Description saved. Support is assessed separately from qualification.",
      );
    });
  };
  $("spec-form").addEventListener("input", (e) => {
    advanced = e.target.id === "spec-json";
    if (advanced) {
      $("spec-form")
        .querySelectorAll("input,select,textarea")
        .forEach((n) => {
          if (n.id !== "spec-json" && n.id !== "spec-linked") n.disabled = true;
        });
      notice(
        "Advanced JSON is the complete description. Reload the saved description or choose New description to return to guided fields.",
      );
    }
    $("spec-status").textContent = "Unsaved description changes";
    $("spec-propose").disabled = true;
    $("spec-review").disabled = true;
  });
  $("spec-show-json").onclick = () => {
    advanced = false;
    $("spec-json").value = JSON.stringify(facts(), null, 2);
    advanced = true;
  };
  $("spec-new").onclick = () => {
    current = null;
    advanced = false;
    additionalChannels = [];
    $("spec-form").reset();
    $("spec-form")
      .querySelectorAll("input,select,textarea,button")
      .forEach((n) => (n.disabled = false));
    $("spec-status").textContent = "New description";
    $("spec-report").replaceChildren();
    $("spec-propose").disabled = true;
    $("spec-review").disabled = true;
    $("spec-title").focus();
  };
  $("spec-propose").onclick = () =>
    action(async () => {
      fill(
        await api(`bench-specs/${current.id}/propose`, {
          expected_revision: current.revision,
        }),
      );
      await refresh();
      notice("Exact description submitted for independent review.");
    });
  $("spec-review").onclick = () =>
    action(async () => {
      fill(
        await api(`bench-specs/${current.id}/review`, {
          expected_revision: current.revision,
          content_hash: current.content_hash,
        }),
      );
      await refresh();
      notice(
        "Description reviewed. No configuration or execution authority granted.",
      );
    });
  $("asset").addEventListener("change", () => {
    current = null;
    $("spec-new").click();
    refresh();
  });
  document.addEventListener("journalnavigate", (e) => {
    if (e.detail.route === "benches") refresh();
  });
  refresh();
}
