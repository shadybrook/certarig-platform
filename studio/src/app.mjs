import { get, post, refreshContract, store, toastText } from "./api.mjs";

const $ = (sel) => document.querySelector(sel);
const views = [...document.querySelectorAll(".view")];
const toast = $("#toast");
let health = {};
let state = {};
let sessionId = store.agentSession || null;
let poll = null;
let startLockUntil = 0;

function showToast(message, bad = false) {
  toast.textContent = message;
  toast.classList.toggle("hidden", false);
  toast.style.borderColor = bad ? "var(--bad)" : "var(--line)";
  setTimeout(() => toast.classList.add("hidden"), 4000);
}

function fail(error) {
  showToast(toastText(error), true);
  if (error.status === 428 || error.code === "approval_required") activate("approvals");
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function activate(name) {
  views.forEach((view) => view.classList.toggle("hidden", view.dataset.view !== name));
  document.querySelectorAll("#nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.view === name);
  });
  store.setView(name);
  if (location.hash.replace("#", "") !== name) {
    location.hash = name;
    return;
  }
  render();
}

function gate(open) {
  $("#gate").hidden = !open;
}

async function login(event) {
  event.preventDefault();
  store.set($("#operator-key").value.trim(), $("#operator-name").value.trim() || "studio-operator");
  try {
    if ($("#mint-session")?.checked) {
      const session = await post("/v1/auth/session", {
        operator_key: store.operatorKey,
        name: store.name,
      });
      store.setSession(session.token);
    }
    await refreshContract();
    health = await get("/health");
    gate(false);
    startPolling();
    activate(store.view || location.hash.replace("#", "") || "telemetry");
  } catch (error) {
    $("#login-error").hidden = false;
    $("#login-error").textContent = error.message;
    store.clear();
  }
}

function logout() {
  store.clear();
  sessionId = null;
  if (poll) clearInterval(poll);
  gate(true);
}

function startPolling() {
  if (poll) clearInterval(poll);
  poll = setInterval(async () => {
    try {
      health = await get("/health");
      state = await get("/v1/live/state");
      const provider = health.agent_provider || "fake";
      $("#health-pill").dataset.state = "ok";
      $("#health-pill").textContent = `${health.hardware_mode} · ${health.rig_id} · ${provider}`;
      const approvals = await get("/v1/approvals?status=pending");
      const n = (approvals.approvals || []).length;
      $("#approval-count").textContent = n;
      $("#approval-count").classList.toggle("hidden", n === 0);
      const visible = document.querySelector(".view:not(.hidden)");
      if (visible && ["telemetry", "approvals"].includes(visible.dataset.view)) render();
      if (visible?.dataset.view === "procedures") await renderProcedures();
    } catch {
      $("#health-pill").dataset.state = "down";
      $("#health-pill").textContent = "offline";
    }
  }, 400);
}

const CHART_COLORS = ["#3d8bfd", "#4cc2c0", "#f5c14a", "#c084fc"];

function inferConcept(sample) {
  if (sample?.concept) return sample.concept;
  const id = String(sample?.channel_id || "").toLowerCase();
  if (id.includes("pressure")) return "pressure";
  if (id.includes("flow")) return "flow";
  if (id.includes("temp")) return "temperature";
  return sample?.channel_id || "";
}

function channelMax(sample) {
  const trip = sample.limits?.trip?.[1];
  if (Number.isFinite(Number(trip)) && Number(trip) > 0) return Number(trip) * 1.4;
  const concept = inferConcept(sample);
  if (concept === "temperature" || sample.unit === "degC") return 120;
  if (String(sample.channel_id || "").includes("pressure") || concept === "pressure") return 10;
  if (String(sample.channel_id || "").includes("flow") || concept === "flow") return 20;
  return Math.max(1, Number(sample.value) * 2 || 10);
}

function historyValue(row, sample) {
  if (!row || typeof row !== "object") return NaN;
  const concept = inferConcept(sample);
  const keys = [`${sample.channel_id}_value`, sample.channel_id, concept];
  if (concept === "pressure") keys.push("pressure_bar", "pressure");
  if (concept === "flow") keys.push("flow_l_min", "flow");
  for (const key of keys) {
    if (row[key] == null || row[key] === "") continue;
    const value = Number(row[key]);
    if (Number.isFinite(value)) return value;
  }
  const nested = (row.samples || []).find((item) => item.channel_id === sample.channel_id || item.concept === concept);
  return nested == null ? NaN : Number(nested.value);
}

function analogSeries() {
  const guard = Object.fromEntries((state.guardrail?.channels || []).map((channel) => [channel.channel_id, channel]));
  return (state.samples || []).map((sample, index) => {
    const extra = guard[sample.channel_id] || {};
    return {
      ...sample,
      concept: inferConcept({ ...sample, concept: extra.concept || sample.concept }),
      unit: sample.unit || extra.unit || "",
      safe_max: Number(extra.safe_max),
      color: CHART_COLORS[index % CHART_COLORS.length],
    };
  });
}

function liveChart(history, series) {
  const rows = (history || []).slice(-300);
  if (!series.length) return "";
  if (rows.length < 2) {
    return `<article class="card live-chart-card" id="live-chart">
      <p class="eyebrow">Live pots</p>
      <p class="muted">Waiting for a rolling telemetry window…</p>
    </article>`;
  }
  const width = 920;
  const left = 52;
  const right = 24;
  const header = 22;
  const paneHeight = 110;
  const gap = 28;
  const height = header + series.length * (paneHeight + gap);
  const panes = series
    .map((sample, index) => {
      const top = header + index * (paneHeight + gap);
      const bottom = top + paneHeight;
      const max = channelMax(sample);
      const values = rows.map((row) => historyValue(row, sample));
      const finite = values.filter(Number.isFinite);
      const latest = finite.at(-1);
      const path = values
        .map((value, n) => {
          const x = left + (n / Math.max(1, values.length - 1)) * (width - left - right);
          const clamped = Number.isFinite(value) ? Math.max(0, Math.min(max, value)) : 0;
          const y = bottom - (clamped / max) * (bottom - top);
          return `${n ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
      const trip = Number(sample.safe_max);
      const tripY = Number.isFinite(trip) && trip > 0 && trip < max ? bottom - (trip / max) * (bottom - top) : null;
      return `
        <text x="${left}" y="${top - 6}" class="chart-title">${esc(sample.channel_id)} · 0–${max} ${esc(sample.unit)}${Number.isFinite(latest) ? ` · ${latest.toFixed(2)} ${esc(sample.unit)}` : ""}</text>
        <line x1="${left}" x2="${width - right}" y1="${top}" y2="${top}" class="chart-grid" />
        <line x1="${left}" x2="${width - right}" y1="${bottom}" y2="${bottom}" class="chart-grid" />
        ${
          tripY == null
            ? ""
            : `<line x1="${left}" x2="${width - right}" y1="${tripY.toFixed(1)}" y2="${tripY.toFixed(1)}" class="chart-limit" />
               <text x="${left + 6}" y="${(tripY - 6).toFixed(1)}" class="chart-limit-label">${esc(String(trip))} ${esc(sample.unit)} trip</text>`
        }
        <path d="${path}" fill="none" stroke="${sample.color}" stroke-width="2.2" data-series="${esc(sample.channel_id)}" />`;
    })
    .join("");
  const legend = series
    .map((sample) => `<span class="chart-legend-item"><i style="background:${sample.color}"></i>${esc(sample.channel_id)}</span>`)
    .join("");
  return `<article class="card live-chart-card" id="live-chart">
    <div class="row">
      <p class="eyebrow">Live pots</p>
      <div class="chart-legend">${legend}</div>
    </div>
    <svg class="chart chart-dual" viewBox="0 0 ${width} ${height}" role="img" aria-label="Live potentiometer telemetry">
      ${panes}
    </svg>
  </article>`;
}

function readyCard() {
  const ready = health.ready_to_arm || {};
  const rows = [
    ["Actuation", ready.actuation_enabled ? "armed" : "held"],
    ["Observe only", ready.observe_only ? "yes" : "no"],
    ["Clean boot", ready.unclean_shutdown ? "unclean" : "clean"],
    ["Twin gate", ready.twin_gate ? "fresh" : "n/a"],
    ["Provider", health.agent_provider || "fake"],
  ];
  return `<article class="card" id="ready-to-arm">
      <p class="eyebrow">Ready to arm</p>
      <ul>${rows.map(([k, v]) => `<li>${esc(k)}: <strong>${esc(v)}</strong></li>`).join("")}</ul>
      <p class="muted">Contract ${esc(String(ready.contract_hash || health.contract_hash || "").slice(0, 16))}…</p>
    </article>`;
}

function shiftCard() {
  const trips = (state.history || [])
    .flatMap((row) => row.events || [])
    .filter((e) => String(e.event || e).includes("forced_safe"))
    .slice(-8);
  return `<article class="card" id="shift-card">
      <p class="eyebrow">Shift</p>
      <p>Recent trips: ${trips.length ? trips.map((e) => esc(e.event || e)).join(", ") : "none this window"}</p>
      <p>Pending approvals: <span id="shift-approvals">${esc($("#approval-count")?.textContent || "0")}</span></p>
    </article>`;
}

function renderTelemetry() {
  const samples = state.samples || [];
  const g = state.guardrail || {};
  const cards = samples
    .map((s) => {
      const max = channelMax(s);
      const pct = Math.max(0, Math.min(100, (Number(s.value) / max) * 100));
      return `<article class="card" data-channel="${esc(s.channel_id)}">
        <div class="row"><span>${esc(s.channel_id)}</span><strong>${esc(s.quality || "")}</strong></div>
        <div class="sensor-reading"><strong data-testid="${esc(s.channel_id)}-value">${Number(s.value).toFixed(2)}</strong> ${esc(s.unit)}</div>
        <div class="meter"><i style="width:${pct}%"></i></div>
      </article>`;
    })
    .join("");
  const sim = health.extensions?.includes("simulator")
    ? `<div class="card sim-sliders" id="sim-controls">
        <p class="eyebrow">Simulator</p>
        <h3>Drive the twin</h3>
        ${(state.samples || [])
          .map(
            (s) => `<label>${esc(s.channel_id)}
              <input type="range" min="0" max="${channelMax(s)}" step="0.05"
                data-testid="sim-${esc(s.channel_id)}"
                data-channel="${esc(s.channel_id)}" value="${Number(s.value).toFixed(2)}" /></label>`
          )
          .join("")}
        <button type="button" id="sim-estop" class="danger">Toggle E-stop</button>
      </div>`
    : "";
  $("#view-telemetry").innerHTML = `
    <h1>Live bench</h1>
    <div class="grid cards">
      ${readyCard()}
      ${shiftCard()}
      <article class="card">
        <p class="eyebrow">Guardrail</p>
        <strong id="guardrail-reason">${esc(g.reason)}</strong>
        <p>E-stop ${g.estop_active ? "ACTIVE" : "released"} · trip ${g.trip_latched ? "latched" : "clear"}</p>
        <p>Output <strong id="output-state">${state.outputs?.gpio23_command_high ? "HIGH" : "off"}</strong></p>
      </article>
      ${cards}
    </div>
    ${liveChart(state.history, analogSeries())}
    <div class="card" style="margin-top:12px">
      <button id="cmd-safe" class="danger" type="button">Force safe</button>
      <button id="cmd-reset" type="button">Reset trip</button>
      <button id="cmd-permit" class="primary" type="button">Request permit</button>
    </div>
    ${sim}`;
}

async function renderProcedures() {
  const [library, runs] = await Promise.all([get("/v1/procedures"), get("/v1/procedure_runs")]);
  const stored = store.runId;
  let detail = null;
  if (stored) {
    try {
      detail = await get(`/v1/procedure_runs/${stored}`);
    } catch {
      detail = null;
    }
  }
  if (!detail) {
    const fallback = (runs.runs || []).find((r) => !r.terminal) || (runs.runs || [])[0];
    detail = fallback ? await get(`/v1/procedure_runs/${fallback.run_id}`) : null;
    if (detail?.run_id && !stored) store.setRunId(detail.run_id);
  }
  if (!$("#proc-id")) {
    $("#view-procedures").innerHTML = `
      <h1>Procedures</h1>
      <div class="card">
        <label>Run <select id="proc-id"></select></label>
        <button id="proc-start" class="primary" type="button">Start</button>
        <button id="proc-abort" class="danger" type="button">Abort</button>
      </div>
      <div id="procedure-coach"></div>
      <div id="procedure-detail"></div>`;
  }
  const select = $("#proc-id");
  const previous = detail?.procedure_id || select.value;
  select.innerHTML = (library.procedures || [])
    .map((p) => `<option value="${esc(p.id)}">${esc(p.title || p.id)}</option>`)
    .join("");
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  const abort = $("#proc-abort");
  if (abort) abort.disabled = !detail;
  const steps = (detail?.steps || [])
    .map(
      (s) => `<li data-status="${esc(s.status)}" data-step="${esc(s.step_id)}">
        <strong>${esc(s.step_id)}</strong> · ${esc(s.type)} · ${esc(s.status)}
        ${s.instruction ? `<div class="instruction" data-testid="instruction">${esc(s.instruction)}</div>` : ""}
        ${s.status === "awaiting" ? `<button data-ack="${esc(s.step_id)}" class="primary">Acknowledge</button>` : ""}
      </li>`
    )
    .join("");
  $("#procedure-coach").innerHTML = triggerCoach(detail);
  $("#procedure-detail").innerHTML = detail
    ? `<div class="card" id="active-run" data-run="${esc(detail.run_id)}" data-status="${esc(detail.status)}">
            <p class="eyebrow">Active run</p>
            <h2>${esc(detail.procedure_id)} · <span id="run-status">${esc(detail.status)}</span></h2>
            <p>${esc(detail.outcome_reason || "")}</p>
            <ol class="steps">${steps}</ol>
          </div>`
    : "<p>No active run.</p>";
}

function triggerCoach(detail) {
  const current = (detail?.steps || []).find((s) => s.step_id === detail?.current_step);
  if (!current || current.type !== "trigger") return "";
  const coach = current.detail?.trigger || {};
  const instruction = coach.instruction || current.instruction || "";
  if (!instruction) return "";
  const live = (coach.signals || [])
    .map((concept) => {
      const row = (state.guardrail?.channels || []).find((c) => c.concept === concept || c.channel_id === concept);
      const sample = (state.samples || []).find((s) => inferConcept(s) === concept || s.channel_id === concept);
      const value = row?.value ?? sample?.value;
      const unit = row?.unit || sample?.unit || "";
      return `${concept} now ${value == null || value === "" ? "—" : Number(value).toFixed(2)} ${unit}`;
    })
    .join(" · ");
  return `<div class="trigger-coach" id="trigger-coach" data-testid="trigger-coach">
      <p class="eyebrow">Operator move</p>
      <p class="trigger-pot">${esc(coach.pot || "Pot")} · target ${esc(coach.target || "see instruction")}</p>
      <p class="trigger-instruction">${esc(instruction)}</p>
      <p class="trigger-live" data-testid="trigger-live">${esc(live || "Waiting for a live sample…")}</p>
    </div>`;
}

async function renderApprovals() {
  const { approvals } = await get("/v1/approvals");
  $("#view-approvals").innerHTML = `
    <h1>Approval inbox</h1>
    ${(approvals || [])
      .map(
        (a) => `<article class="card" data-approval="${esc(a.approval_id)}">
          <strong>${esc(a.tool)}</strong> · ${esc(a.status)}
          <p>${esc(a.reason)}</p>
          ${
            a.status === "pending"
              ? `<button data-grant="${esc(a.approval_id)}" class="primary">Grant</button>
                 <button data-deny="${esc(a.approval_id)}" class="danger">Deny</button>`
              : ""
          }
        </article>`
      )
      .join("") || "<p>No approval requests.</p>"}`;
}

async function renderAgent() {
  if ($("#agent-log")) return;
  let prior = "";
  if (sessionId) {
    try {
      const session = await get(`/v1/agent/sessions/${sessionId}`);
      prior = `<pre class="muted">${esc(JSON.stringify(session, null, 2).slice(0, 2000))}</pre>`;
    } catch {
      sessionId = null;
    }
  }
  $("#view-agent").innerHTML = `
    <h1>Agent <span class="pill" id="agent-provider">${esc(health.agent_provider || "fake")}</span></h1>
    ${prior}
    <div id="agent-log" class="chat"></div>
    <form id="agent-form" class="card">
      <label>Ask the agent
        <input id="agent-text" required placeholder="run the relay truth table" />
      </label>
      <button class="primary" type="submit">Send</button>
    </form>`;
}

async function renderEvidence() {
  const listing = await get("/v1/evidence");
  $("#view-evidence").innerHTML = `
    <h1>Evidence</h1>
    <div class="card"><button id="export-all" class="primary" type="button">Export bundle</button></div>
    <h2>Runs</h2>
    <table><thead><tr><th>Run</th><th>Procedure</th><th>Status</th><th>Files</th></tr></thead>
    <tbody>${(listing.runs || [])
      .map(
        (r) => `<tr><td>${esc(r.run_id)}</td><td>${esc(r.procedure_id)}</td><td>${esc(r.status)}</td>
        <td><a href="/v1/evidence/runs/${esc(r.run_id)}" data-run="${esc(r.run_id)}">open</a></td></tr>`
      )
      .join("")}</tbody></table>
    <h2>Recordings</h2>
    <ul>${(listing.recordings || [])
      .map((f) => `<li><a href="${esc(f.path)}">${esc(f.name)}</a> <code>${esc(f.sha256).slice(0, 12)}…</code></li>`)
      .join("")}</ul>
    <h2>Exports</h2>
    <ul>${(listing.exports || [])
      .map((f) => `<li><a href="${esc(f.path)}">${esc(f.name)}</a> <code>${esc(f.sha256).slice(0, 12)}…</code></li>`)
      .join("")}</ul>`;
}

function policySelect(name, policy) {
  const locked = name === "bypass_interlock" || name === "override_limits";
  const options = ["allowed", "human_approval", "never"]
    .map((p) => `<option value="${p}" ${p === policy ? "selected" : ""}>${p}</option>`)
    .join("");
  return `<select data-cap="${esc(name)}" data-testid="cap-${esc(name)}" ${locked ? "disabled" : ""}>${options}</select>`;
}

async function renderCapabilities() {
  const caps = await get("/v1/capabilities");
  const tools = (caps.tools || [])
    .map((t) => `<tr><td>${esc(t.name)}</td><td>${policySelect(t.name, t.policy)}</td><td>${esc(t.note || t.description || "")}</td></tr>`)
    .join("");
  $("#view-capabilities").innerHTML = `
    <h1>What the agent may do</h1>
    <p>Manifest ${esc(caps.manifest_id)} · contract ${esc(caps.contract_hash || "").slice(0, 16)}…</p>
    <table><thead><tr><th>Tool</th><th>Policy</th><th>Why</th></tr></thead><tbody>${tools}</tbody></table>
    <button id="caps-propose" type="button">Preview policy apply</button>
    <button id="caps-apply" class="primary" type="button">Apply policies</button>
    <pre id="caps-diff" data-testid="caps-diff"></pre>`;
  $("#view-capabilities")._document = caps.document;
}

async function renderAuthor() {
  const [templates, signals, drafts, ledger] = await Promise.all([
    get("/v1/authoring/templates"),
    get("/v1/signals"),
    get("/v1/procedures/drafts"),
    get("/v1/ledger"),
  ]);
  const options = (templates.templates || []).map((t) => `<option value="${esc(t.id)}">${esc(t.title)}</option>`).join("");
  const signalOpts = (signals.signals || [])
    .filter((s) => s.concept !== "emergency_stop")
    .map((s) => `<option value="${esc(s.channel_id)}" data-concept="${esc(s.concept)}">${esc(s.channel_id)} (${esc(s.concept)})</option>`)
    .join("");
  const draftCards = (drafts.drafts || [])
    .map(
      (d) => `<article class="card" data-draft="${esc(d.procedure_hash)}">
        <strong>${esc(d.id || d.procedure_id)}</strong>
        <p>${esc(d.title || "")}</p>
        <button data-approve="${esc(d.procedure_hash)}" class="primary">Approve</button>
        <button data-reject="${esc(d.procedure_hash)}" class="danger">Reject</button>
      </article>`
    )
    .join("");
  const outcomes = (ledger.outcomes || [])
    .slice(-8)
    .reverse()
    .map((o) => `<li>${esc(o.procedure_id)} · ${esc(o.status)} · ${esc(o.first_failing_step || "—")}</li>`)
    .join("");
  $("#view-author").innerHTML = `
    <h1>Author a procedure</h1>
    <div class="grid cards">
      <form id="author-form" class="card">
        <label>Template <select id="author-template" data-testid="author-template">${options}</select></label>
        <label>Signal <select id="author-signal" data-testid="author-signal">${signalOpts}</select></label>
        <label>Trip / limit <input id="author-trip" type="number" step="0.1" value="4.2" /></label>
        <label>Hold seconds <input id="author-hold" type="number" step="0.1" value="2" /></label>
        <label>Title <input id="author-title" type="text" placeholder="optional" /></label>
        <button id="author-validate" type="button">Validate</button>
        <button id="author-draft" class="primary" type="button">Save draft</button>
        <pre id="author-errors" class="muted"></pre>
      </form>
      <aside class="card">
        <p class="eyebrow">Recent outcomes</p>
        <ul id="author-ledger">${outcomes || "<li>No ledger rows yet.</li>"}</ul>
      </aside>
    </div>
    <h2>Drafts</h2>
    ${draftCards || "<p>No drafts. Validate and save one.</p>"}`;
}

function collectOnboardDocument() {
  const current = $("#view-onboard")._document;
  if (!current) throw new Error("no writable rig document on this node");
  const next = structuredClone(current);
  const originals = next.channels || [];
  const channels = [];
  document.querySelectorAll("#onboard-channels tr").forEach((tr) => {
    const inputs = [...tr.querySelectorAll("input[data-field]")];
    if (!inputs.length) return;
    const index = Number(inputs[0].dataset.ch);
    const base = originals[index]
      ? structuredClone(originals[index])
      : {
          channel_id: "new_signal",
          kind: "analog",
          concept: "signal",
          unit: "unit",
          valid_min: 0,
          valid_max: 100,
          safe_min: 0,
          safe_max: 50,
          required: true,
          calibration_id: "UNCAL-new_signal",
        };
    inputs.forEach((input) => {
      base[input.dataset.field] = input.type === "number" ? Number(input.value) : input.value;
    });
    channels.push(base);
  });
  next.channels = channels;
  return next;
}

function collectCapsDocument(root) {
  const source = root?._document || root?._capsDocument || $("#view-onboard")?._capsDocument;
  if (!source) throw new Error("no writable capabilities document on this node");
  const next = structuredClone(source);
  next.tools = next.tools || {};
  (root || document).querySelectorAll("select[data-cap]").forEach((sel) => {
    const name = sel.dataset.cap;
    next.tools[name] = { ...(next.tools[name] || {}), policy: sel.value };
  });
  return next;
}

async function renderOnboard() {
  const [rig, caps] = await Promise.all([get("/v1/rig"), get("/v1/capabilities")]);
  const mode = rig.rig.hardware.mode;
  const adapters = ["mock", "simulator", "raspberry_pi", "mqtt", "modbus_tcp", "opcua"];
  const real = new Set(["mock", "simulator", "raspberry_pi", "mqtt", "modbus_tcp"]);
  const channels = (rig.document?.channels || rig.rig.channels || [])
    .map(
      (s, i) => `<tr data-row="${i}">
        <td><input data-ch="${i}" data-field="channel_id" value="${esc(s.channel_id)}" /></td>
        <td><input data-ch="${i}" data-field="concept" value="${esc(s.concept || "")}" /></td>
        <td><input data-ch="${i}" data-field="unit" value="${esc(s.unit)}" /></td>
        <td><input data-ch="${i}" data-field="safe_max" type="number" step="0.1" value="${esc(s.safe_max)}" /></td>
        <td><button type="button" data-remove-ch="${i}" data-testid="onboard-remove-${i}">Remove</button></td>
      </tr>`
    )
    .join("");
  const capRows = (caps.tools || [])
    .map((t) => `<tr><td>${esc(t.name)}</td><td>${policySelect(t.name, t.policy)}</td></tr>`)
    .join("");
  $("#view-onboard").innerHTML = `
    <h1>Onboard this rig</h1>
    <div class="card">
      <p class="eyebrow">1 · Connect</p>
      <p>Node ${esc(rig.rig.rig_id)} revision ${esc(rig.rig.revision)}</p>
    </div>
    <div class="card">
      <p class="eyebrow">2 · Interface</p>
      <div class="adapters">${adapters
        .map(
          (a) =>
            `<span class="${a === mode ? "on" : ""}">${esc(a)}${
              a === mode ? " (active)" : real.has(a) ? "" : " — roadmap"
            }</span>`
        )
        .join("")}</div>
      <p class="muted">MQTT and Modbus TCP are observe-mode adapters today. OPC-UA is still a roadmap label.</p>
    </div>
    <div class="card">
      <p class="eyebrow">3 · Signals (writes a preview, then apply)</p>
      <table><thead><tr><th>Channel</th><th>Concept</th><th>Unit</th><th>Safe max</th><th></th></tr></thead>
      <tbody id="onboard-channels">${channels}</tbody></table>
      <button id="onboard-add" type="button" data-testid="onboard-add">Add channel</button>
      <button id="onboard-propose" type="button">Preview apply</button>
      <button id="onboard-apply" class="primary" type="button">Apply</button>
      <pre id="onboard-diff" data-testid="onboard-diff"></pre>
    </div>
    <div class="card">
      <p class="eyebrow">4 · Capabilities</p>
      <p>${esc(caps.description || caps.manifest_id)}</p>
      <table><thead><tr><th>Tool</th><th>Policy</th></tr></thead><tbody>${capRows}</tbody></table>
      <button id="onboard-caps-propose" type="button">Preview policies</button>
      <button id="onboard-caps-apply" class="primary" type="button">Apply policies</button>
      <pre id="onboard-caps-diff" data-testid="onboard-caps-diff"></pre>
    </div>
    <div class="card">
      <p class="eyebrow">5 · Bench briefing</p>
      <p class="muted">Typed context copied into every evidence bundle. This is not auto-mapping.</p>
      <label>P1 role <input id="brief-p1" data-testid="brief-p1" type="text" placeholder="Pressure emulator, ADS1115 A0" /></label>
      <label>P2 role <input id="brief-p2" data-testid="brief-p2" type="text" placeholder="Flow emulator, ADS1115 A1" /></label>
      <label>E-stop <input id="brief-estop" data-testid="brief-estop" type="text" placeholder="GPIO24 mushroom" /></label>
      <label>Relay <input id="brief-relay" data-testid="brief-relay" type="text" placeholder="GPIO23 permit / indicator" /></label>
      <label>Diagram notes <textarea id="brief-notes" data-testid="brief-notes" rows="3" placeholder="Optional as-built notes or diagram path on this node"></textarea></label>
      <button id="brief-save" class="primary" type="button">Save briefing</button>
      <p id="brief-status" class="muted" data-testid="brief-status"></p>
    </div>
    <div class="card">
      <p class="eyebrow">6 · Commissioning facts</p>
      <p class="muted">The agent must learn these facts. It can ask in any order. One description can fill every slot. A labeled photo is optional context. A human applies the map. A photo never arms the relay.</p>
      <ul id="interview-needs" data-testid="interview-needs"></ul>
      <p id="interview-prompt" data-testid="interview-prompt">Not started.</p>
      <label>Describe the bench <textarea id="interview-text" data-testid="interview-text" rows="4" placeholder="Pots, E-stop, relay. P1 pressure trip 4.2 bar. P2 flow 15 L/min. Nothing observe-only."></textarea></label>
      <label>Bench photo (optional) <input id="interview-image" data-testid="interview-image" type="file" accept="image/png,image/jpeg,image/webp" /></label>
      <p id="interview-image-status" class="muted" data-testid="interview-image-status"></p>
      <button id="interview-start" type="button" data-testid="interview-start">Start</button>
      <button id="interview-next" class="primary" type="button" data-testid="interview-record">Record facts</button>
      <button id="interview-propose" type="button" data-testid="interview-propose">Propose map</button>
      <button id="interview-apply" class="primary" type="button" data-testid="interview-apply">Confirm apply</button>
      <pre id="interview-diff" data-testid="interview-diff"></pre>
    </div>`;
  $("#view-onboard").dataset.hash = rig.config_hash;
  $("#view-onboard")._document = rig.document;
  $("#view-onboard")._capsDocument = caps.document;
  try {
    const saved = await get("/v1/ops/briefing");
    const b = saved.briefing || {};
    $("#brief-p1").value = b.p1_role || "";
    $("#brief-p2").value = b.p2_role || "";
    $("#brief-estop").value = b.estop || "";
    $("#brief-relay").value = b.relay || "";
    $("#brief-notes").value = b.diagram_notes || "";
    $("#brief-status").textContent = saved.present ? `Saved ${saved.updated_at || ""}`.trim() : "Not saved yet.";
  } catch {
    $("#brief-status").textContent = "Briefing endpoint unavailable.";
  }
  try {
    const interview = await get("/v1/ops/interview");
    paintInterview(interview);
  } catch {
    $("#interview-prompt").textContent = "Interview endpoint unavailable.";
  }
}

function paintInterview(interview) {
  const missing = new Set(interview.missing || []);
  const needs = interview.needs || [];
  $("#interview-needs").innerHTML = needs
    .map((slot) => {
      const filled = !missing.has(slot.id) && interview.status !== "idle";
      const mark = filled ? "known" : slot.required ? "need" : "optional";
      return `<li data-slot="${esc(slot.id)}" data-state="${mark}">${esc(slot.id)} · ${esc(slot.need)}</li>`;
    })
    .join("");
  $("#interview-prompt").textContent = interview.prompt || interview.status || "Not started.";
  const images = interview.images || [];
  const status = $("#interview-image-status");
  if (status) {
    status.textContent = images.length
      ? `Stored ${images.length} photo(s); diagram slot ${interview.answers?.diagram || images.at(-1)?.path}. A photo never arms the relay.`
      : "No photo attached. Optional. A human still applies.";
  }
}

async function render() {
  const name = document.querySelector(".view:not(.hidden)")?.dataset.view || "telemetry";
  try {
    if (name === "telemetry") renderTelemetry();
    else if (name === "procedures") await renderProcedures();
    else if (name === "approvals") await renderApprovals();
    else if (name === "agent") await renderAgent();
    else if (name === "evidence") await renderEvidence();
    else if (name === "capabilities") await renderCapabilities();
    else if (name === "author") await renderAuthor();
    else if (name === "onboard") await renderOnboard();
  } catch (error) {
    fail(error);
  }
}

async function authorProcedure() {
  const signalEl = $("#author-signal");
  const concept = signalEl?.selectedOptions?.[0]?.dataset.concept;
  const built = await post("/v1/authoring/build", {
    template_id: $("#author-template").value,
    signal: signalEl.value,
    concept,
    trip: Number($("#author-trip").value),
    hold_s: Number($("#author-hold").value),
    title: $("#author-title").value || undefined,
  });
  return built.procedure;
}

document.body.addEventListener("click", async (event) => {
  const t = event.target;
  if (!(t instanceof HTMLElement)) return;
  try {
    if (t.id === "cmd-safe") await post("/v1/live/commands/safe", {});
    if (t.id === "cmd-reset") await post("/v1/live/commands/reset", {});
    if (t.id === "cmd-permit") await post("/v1/live/commands/permit", {});
    if (t.id === "sim-estop") await post("/v1/sim/estop", { pressed: !state.guardrail?.estop_active });
    if (t.id === "proc-start") {
      const current = $("#active-run");
      const live = current && !["passed", "failed", "aborted", "cancelled"].includes(current.dataset.status || "");
      if (live || Date.now() < startLockUntil) {
        if (live) showToast("Abort the current run before starting another");
        return;
      }
      startLockUntil = Date.now() + 1500;
      const id = $("#proc-id").value;
      const started = await post("/v1/procedure_runs", { procedure_id: id });
      store.setRunId(started.run_id || started.run?.run_id);
      await renderProcedures();
    }
    if (t.id === "proc-abort") {
      const run = $("#active-run")?.dataset.run;
      if (run) await post(`/v1/procedure_runs/${run}/abort`, { reason: "operator abort from Studio" });
    }
    if (t.dataset.ack) {
      const run = $("#active-run").dataset.run;
      await post(`/v1/procedure_runs/${run}/ack`, { step_id: t.dataset.ack });
    }
    if (t.dataset.grant) await post(`/v1/approvals/${t.dataset.grant}/grant`, {});
    if (t.dataset.deny) await post(`/v1/approvals/${t.dataset.deny}/deny`, {});
    if (t.id === "export-all") {
      const bundle = await post("/v1/ops/evidence/export", {});
      showToast(`Exported ${bundle.filename}`);
      await renderEvidence();
    }
    if (t.id === "author-validate") {
      const procedure = await authorProcedure();
      const result = await post("/v1/procedures/validate", { procedure });
      $("#author-errors").textContent = result.valid ? "Valid." : (result.errors || []).join("\n");
      $("#view-author")._procedure = procedure;
    }
    if (t.id === "author-draft") {
      const procedure = $("#view-author")._procedure || (await authorProcedure());
      await post("/v1/procedures/drafts", { procedure });
      showToast("Draft saved");
      await renderAuthor();
    }
    if (t.dataset.approve) {
      await post(`/v1/procedures/drafts/${t.dataset.approve}/approve`, {});
      showToast("Draft approved");
      await renderAuthor();
    }
    if (t.dataset.reject) {
      await post(`/v1/procedures/drafts/${t.dataset.reject}/reject`, {});
      await renderAuthor();
    }
    if (t.id === "onboard-add") {
      const current = $("#view-onboard")._document;
      if (!current) throw new Error("no writable rig document on this node");
      if (!current.channels) current.channels = [];
      const i = current.channels.length;
      current.channels.push({
        channel_id: `signal_${i + 1}`,
        kind: "analog",
        concept: "signal",
        unit: "unit",
        valid_min: 0,
        valid_max: 100,
        safe_min: 0,
        safe_max: 50,
        required: true,
        calibration_id: `UNCAL-signal_${i + 1}`,
      });
      $("#onboard-channels").insertAdjacentHTML(
        "beforeend",
        `<tr data-row="${i}">
          <td><input data-ch="${i}" data-field="channel_id" value="signal_${i + 1}" /></td>
          <td><input data-ch="${i}" data-field="concept" value="signal" /></td>
          <td><input data-ch="${i}" data-field="unit" value="unit" /></td>
          <td><input data-ch="${i}" data-field="safe_max" type="number" step="0.1" value="50" /></td>
          <td><button type="button" data-remove-ch="${i}" data-testid="onboard-remove-${i}">Remove</button></td>
        </tr>`
      );
    }
    if (t.dataset.removeCh) {
      t.closest("tr")?.remove();
    }
    if (t.id === "onboard-propose" || t.id === "onboard-apply") {
      try {
        const next = collectOnboardDocument();
        const preview = await post("/v1/rig/propose", { document: next });
        $("#onboard-diff").textContent = `${(preview.diff || []).join("\n")}\nnext ${preview.next_hash}`;
        if (t.id === "onboard-apply") {
          await post("/v1/rig/apply", { document: next, expected_current_hash: preview.current_hash });
          showToast("Rig config applied");
          await renderOnboard();
        }
      } catch (error) {
        $("#onboard-diff").textContent = toastText(error);
        throw error;
      }
    }
    if (t.id === "onboard-caps-propose" || t.id === "onboard-caps-apply" || t.id === "caps-propose" || t.id === "caps-apply") {
      const next = collectCapsDocument(t.id.startsWith("onboard") ? $("#view-onboard") : $("#view-capabilities"));
      const preview = await post("/v1/capabilities/propose", { document: next });
      const diffEl = t.id.startsWith("onboard") ? $("#onboard-caps-diff") : $("#caps-diff");
      if (diffEl) diffEl.textContent = `${(preview.diff || []).join("\n")}\nnext ${preview.next_hash}`;
      if (t.id.endsWith("-apply")) {
        await post("/v1/capabilities/apply", { document: next, expected_current_hash: preview.current_hash });
        showToast("Capability policies applied");
        if (t.id.startsWith("onboard")) await renderOnboard();
        else await renderCapabilities();
      }
    }
    if (t.id === "interview-start") {
      const started = await post("/v1/ops/interview/start", {});
      paintInterview(started);
      $("#interview-text").value = "";
      $("#interview-diff").textContent = "";
    }
    if (t.id === "interview-next") {
      const answered = await post("/v1/ops/interview/answer", { text: $("#interview-text").value });
      paintInterview(answered);
      $("#interview-text").value = "";
      if (answered.status === "complete") showToast("Required facts are in — propose the map");
    }
    if (t.id === "interview-propose") {
      try {
        const preview = await post("/v1/ops/interview/propose", {});
        $("#view-onboard")._interviewPreview = preview;
        $("#interview-diff").textContent = `${(preview.diff || []).join("\n")}\nnext ${preview.next_hash}`;
      } catch (error) {
        $("#interview-diff").textContent = toastText(error);
        throw error;
      }
    }
    if (t.id === "interview-apply") {
      let preview = $("#view-onboard")._interviewPreview;
      if (!preview) preview = await post("/v1/ops/interview/propose", {});
      await post("/v1/rig/apply", {
        document: preview.document,
        expected_current_hash: preview.current_hash,
      });
      showToast("Interview map applied");
      await renderOnboard();
    }
    if (t.id === "brief-save") {
      const saved = await post("/v1/ops/briefing", {
        p1_role: $("#brief-p1").value,
        p2_role: $("#brief-p2").value,
        estop: $("#brief-estop").value,
        relay: $("#brief-relay").value,
        diagram_notes: $("#brief-notes").value,
      });
      $("#brief-status").textContent = `Saved ${saved.updated_at || ""}`.trim();
      showToast("Bench briefing saved");
    }
    if (t.id === "logout") logout();
  } catch (error) {
    fail(error);
  }
});

document.body.addEventListener("change", async (event) => {
  const t = event.target;
  if (!(t instanceof HTMLInputElement) || t.id !== "interview-image" || !t.files?.[0]) return;
  const file = t.files[0];
  if (file.size > 1_200_000) {
    showToast("Photo must be under 1.2 MB", true);
    t.value = "";
    return;
  }
  try {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    bytes.forEach((b) => {
      binary += String.fromCharCode(b);
    });
    const attached = await post("/v1/ops/interview/image", {
      filename: file.name,
      media_type: file.type,
      content_base64: btoa(binary),
    });
    paintInterview(attached);
    showToast("Bench photo stored as diagram context");
  } catch (error) {
    fail(error);
  }
});

document.body.addEventListener("input", async (event) => {
  const t = event.target;
  if (t instanceof HTMLInputElement && t.dataset.channel) {
    try {
      await post("/v1/sim/set_target", { channel: t.dataset.channel, value: Number(t.value) });
    } catch (error) {
      fail(error);
    }
  }
});

document.body.addEventListener("submit", async (event) => {
  if (event.target.id === "agent-form") {
    event.preventDefault();
    const input = $("#agent-text");
    const log = $("#agent-log");
    const text = input.value.trim();
    input.value = "";
    log.insertAdjacentHTML("beforeend", `<div class="bubble user">${esc(text)}</div>`);
    try {
      const result = await post("/v1/agent/chat", { text, session_id: sessionId });
      sessionId = result.session_id;
      store.setAgentSession(sessionId);
      const tools = (result.tool_calls || []).map((c) => `${c.ok ? "ok" : "refused"} ${c.name}`).join(" · ");
      log.insertAdjacentHTML("beforeend", `<div class="bubble">${esc(result.text)}<div class="tools">${esc(tools)}</div></div>`);
      log.scrollTop = log.scrollHeight;
    } catch (error) {
      fail(error);
    }
  }
});

$("#login-form").addEventListener("submit", login);
$("#nav").addEventListener("click", (event) => {
  const link = event.target.closest("a[data-view]");
  if (!link) return;
  event.preventDefault();
  activate(link.dataset.view);
});
window.addEventListener("hashchange", () => {
  const name = location.hash.replace("#", "") || store.view || "telemetry";
  activate(name);
});

(async function boot() {
  if (!store.operatorKey) {
    gate(true);
    return;
  }
  try {
    await refreshContract();
    health = await get("/health");
    state = await get("/v1/live/state");
    gate(false);
    startPolling();
    activate(location.hash.replace("#", "") || store.view || "telemetry");
  } catch {
    store.clear();
    gate(true);
  }
})();
