import { get, post, refreshContract, store, toastText, headers } from "./api.mjs";

const $ = (sel) => document.querySelector(sel);
const views = [...document.querySelectorAll(".view")];
const toast = $("#toast");
let health = {};
let state = {};
let sessionId = store.agentSession || null;
let poll = null;
let pendingRun = null;
let startingRun = false;
let procedureRenderVersion = 0;

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
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function activate(name) {
  views.forEach((view) => view.classList.toggle("hidden", view.dataset.view !== name));
  document.querySelectorAll("#nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.view === name);
  });
  store.setView(name);
  location.hash = name;
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
      if (visible && ["telemetry", "procedures", "approvals"].includes(visible.dataset.view)) render();
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
  if (startingRun) return;
  const version = ++procedureRenderVersion;
  const storedAtStart = store.runId;
  const selected = $("#proc-id")?.value;
  const [library, runs] = await Promise.all([get("/v1/procedures"), get("/v1/procedure_runs")]);
  const stored = store.runId;
  const match = (runs.runs || []).find((r) => r.run_id === stored);
  const active = match || (runs.runs || []).find((r) => !r.terminal) || (runs.runs || [])[0];
  const detail = active ? await get(`/v1/procedure_runs/${active.run_id}`) : null;
  if (startingRun || version !== procedureRenderVersion || store.runId !== storedAtStart) return;
  if (detail?.run_id) store.setRunId(detail.run_id);
  const list = (library.procedures || []).map((p) => `<option value="${esc(p.id)}">${esc(p.title || p.id)}</option>`).join("");
  const steps = (detail?.steps || [])
    .map(
      (s) => `<li data-status="${esc(s.status)}" data-step="${esc(s.step_id)}">
        <strong>${esc(s.step_id)}</strong> · ${esc(s.type)} · ${esc(s.status)}
        ${s.instruction ? `<div class="instruction" data-testid="instruction">${esc(s.instruction)}</div>` : ""}
        ${s.status === "awaiting" ? `<button data-ack="${esc(s.step_id)}" class="primary">Acknowledge</button>` : ""}
      </li>`
    )
    .join("");
  $("#view-procedures").innerHTML = `
    <h1>Procedures</h1>
    <div class="card">
      <label>Run <select id="proc-id">${list}</select></label>
      <button id="proc-start" class="primary" type="button">Start</button>
      <button id="proc-abort" class="danger" type="button" ${active ? "" : "disabled"}>Abort</button>
    </div>
    ${
      detail
        ? `<div class="card" id="active-run" data-run="${esc(detail.run_id)}" data-status="${esc(detail.status)}">
            <p class="eyebrow">Active run</p>
            <h2>${esc(detail.procedure_id)} · <span id="run-status">${esc(detail.status)}</span></h2>
            <p>${esc(detail.outcome_reason || "")}</p>
            <ol class="steps">${steps}</ol>
          </div>`
        : "<p>No active run.</p>"
    }`;
  if (selected && [...$("#proc-id").options].some(o => o.value === selected)) $("#proc-id").value = selected;
}

async function renderApprovals() {
  const { approvals } = await get("/v1/approvals");
  $("#view-approvals").innerHTML = `
    <h1>Approval inbox</h1>
    ${(approvals || [])
      .map(
        (a) => `<article class="card" data-approval="${esc(a.approval_id)}">
          <strong>${esc(a.tool)}</strong> · ${esc(a.status)}
          <p>${esc(a.reason)}</p><p>Requested by ${esc(a.requested_by)} (${esc(a.requested_role)})</p><pre>${esc(JSON.stringify(a.args, null, 2))}</pre><p>Configuration contract ${esc(a.contract_hash).slice(0,16)}…</p>
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
        <td><button data-export-run="${esc(r.run_id)}">Export this run</button></td></tr>`
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

async function renderCapabilities() {
  const caps = await get("/v1/capabilities");
  const tools = (caps.agent_tools || [])
    .map((t) => `<tr><td>${esc(t.name)}</td><td>${esc(t.policy)}</td><td>${esc(t.description)}</td></tr>`)
    .join("");
  $("#view-capabilities").innerHTML = `
    <h1>What the agent may do</h1>
    <p>Manifest ${esc(caps.manifest_id)} · contract ${esc(caps.contract_hash || "").slice(0, 16)}…</p>
    <table><thead><tr><th>Tool</th><th>Policy</th><th>Why</th></tr></thead><tbody>${tools}</tbody></table>`;
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

async function renderInterview() {
  const {interviews} = await get("/v1/commissioning/interviews");
  const saved = sessionStorage.getItem("commissioning-interview");
  const active = interviews.find(i => i.interview_id === saved) || interviews.at(-1);
  const root = $("#interview-ui");
  root._interview = active;
  const answers = active?.answers || {};
  root.innerHTML = `<h2>Guided commissioning interview</h2>
    <p>Deterministic bounded fixture · proposals cannot energize equipment. Unknown facts remain blockers.</p>
    <button id="iv-create">New interview</button>
    <label>Resume saved interview<select id="iv-resume">${interviews.map(i => `<option value="${esc(i.interview_id)}" ${i === active ? "selected" : ""}>${esc(i.interview_id)} · ${esc(i.status)}</option>`).join("")}</select></label>
    ${active ? `<p>Revision ${active.revision} · ${esc(active.status)}</p>
    <label>Equipment<input id="iv-equipment" value="${esc(answers.equipment || "")}" /></label>
    <label>Safe state<select id="iv-safe"><option value="">Unknown</option><option value="deenergized" ${answers.safe_state === "deenergized" ? "selected" : ""}>Deenergized / output off</option></select></label>
    <label>Supported procedure IDs, comma separated<input id="iv-procedures" value="${esc((answers.procedures || []).join(", "))}" /></label>
    <label>Source reference for these answers<input id="iv-source" value="${esc(active.sources.document || "")}" placeholder="Operator mapping record / fixture specification" /></label>
    <label>Optional bounded text (equipment:, safe_state:, procedures:)<textarea id="iv-text">${esc(active.source_text || "")}</textarea></label>
    <label>Simulator reference template<select id="iv-template"><option value="thermal">Thermal RC plant</option><option value="pressure_flow">Pressure / flow simulator</option></select></label>
    <button id="iv-template-load">Load simulator template into draft</button>
    <label>Proposed signal map, units, scaling and limits (JSON)<textarea id="iv-document" rows="12">${esc(JSON.stringify(answers.document || {}, null, 2))}</textarea></label>
    <label>Calibration evidence (JSON list of calibration_id and reference)<textarea id="iv-calibrations" rows="4">${esc(JSON.stringify(answers.calibration_records || [], null, 2))}</textarea></label>
    <button id="iv-save">Save answers</button><button id="iv-propose">Check and propose</button>
    <button id="iv-apply" ${active.status !== "proposed" ? "disabled" : ""}>Review and apply proposed map</button>
    <ul id="iv-blockers">${(active.blockers || []).map(b => `<li>${esc(b)}</li>`).join("")}</ul>
    <pre id="iv-preview">${esc(active.proposal ? JSON.stringify(active.proposal.revalidation, null, 2) : "")}</pre>` : "<p>Create an interview to begin.</p>"}`;
}

async function renderOnboard() {
  $("#view-onboard").innerHTML = "<p>Loading rig configuration…</p>";
  const [rig, caps, commissioning, library] = await Promise.all([get("/v1/rig"), get("/v1/capabilities"), get("/v1/commissioning"), get("/v1/procedures")]);
  const mode = rig.rig.hardware.mode;
  const adapters = ["mock", "simulator", "raspberry_pi", "mqtt", "modbus_tcp", "opcua"];
  const real = new Set(["mock", "simulator", "raspberry_pi", "mqtt", "modbus_tcp"]);
  const channels = (rig.document?.channels || rig.rig.channels || [])
    .map(
      (s, i) => `<tr>
        <td><input data-ch="${i}" data-field="channel_id" value="${esc(s.channel_id)}" /></td>
        <td><input data-ch="${i}" data-field="concept" value="${esc(s.concept)}" /></td>
        <td><input data-ch="${i}" data-field="unit" value="${esc(s.unit)}" /></td>
        <td><input data-ch="${i}" data-field="safe_max" type="number" step="0.1" value="${esc(s.safe_max)}" /></td>
      </tr>`
    )
    .join("");
  $("#view-onboard").innerHTML = `
    <h1>Onboard this rig</h1><div class="card" id="interview-ui"></div>
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
      <p class="muted">MQTT supports explicit broker observation and a separate in-process fixture. Modbus remains a local scaffold. OPC-UA is planned.</p>
    </div>
    <div class="card">
      <p class="eyebrow">3 · Signals (writes a preview, then apply)</p>
      <table><thead><tr><th>Channel</th><th>Concept</th><th>Unit</th><th>Safe max</th></tr></thead>
      <tbody id="onboard-channels">${channels}</tbody></table>
      <button id="onboard-propose" type="button">Preview apply</button>
      <button id="onboard-apply" class="primary" type="button">Apply</button>
      <pre id="onboard-diff" data-testid="onboard-diff"></pre>
    </div>
    <details class="card"><summary>Full rig configuration</summary>
      <p>Edit channel mappings, units and limits. Preview before applying. Simulator mappings reload locally; physical adapter changes require restart.</p>
      <label>Configuration JSON<textarea id="onboard-document" rows="16">${esc(JSON.stringify(rig.document, null, 2))}</textarea></label>
      <button id="onboard-json-propose" type="button">Preview configuration</button>
      <button id="onboard-json-apply" type="button">Apply configuration</button>
    </details>
    <div class="card" id="commissioning-state" data-status="${esc(commissioning.status)}">
      <h2>Commissioning review</h2>
      <p>${esc(commissioning.evidence_kind)} · ${esc(commissioning.status)}</p>
      <p>Physical commissioning: not accepted by this software review</p>
      <ul>${commissioning.blockers.map(b => `<li>${esc(b)}</li>`).join("")}</ul>
      <label>Procedure to review<select id="commission-procedure">${library.procedures.map(p => `<option value="${esc(p.id)}">${esc(p.title)}</option>`).join("")}</select></label>
      <button id="commission-review" type="button">Review configuration for this procedure</button>
    </div>
    <div class="card">
      <p class="eyebrow">4 · Capabilities</p>
      <p>${esc(caps.description || caps.manifest_id)}</p>
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
    </div>`;
  $("#view-onboard").dataset.hash = rig.config_hash;
  await renderInterview();
  $("#view-onboard")._document = rig.document;
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
      const id = $("#proc-id").value;
      startingRun = true;
      procedureRenderVersion++;
      $("#active-run")?.remove();
      store.setRunId("");
      try {
        let started;
        try {
          started = await post("/v1/procedure_runs", {procedure_id: id});
        } catch (error) {
          if (error.status !== 428) throw error;
          const approval = await post("/v1/approvals/request", {tool: "run_procedure", args: {procedure_id: id}, reason: "Operator requested this named procedure from Studio"});
          pendingRun = {procedure_id: id, approval_id: approval.approval_id};
          activate("approvals");
          return;
        }
        store.setRunId(started.run_id || started.run?.run_id);
      } finally {
        startingRun = false;
      }
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
    if (t.dataset.grant) {
      await post(`/v1/approvals/${t.dataset.grant}/grant`, {});
      if (pendingRun?.approval_id === t.dataset.grant) {
        const started = await post("/v1/procedure_runs", pendingRun);
        pendingRun = null;
        store.setRunId(started.run_id);
        activate("procedures");
      }
    }
    if (t.dataset.deny) { await post(`/v1/approvals/${t.dataset.deny}/deny`, {}); if (pendingRun?.approval_id === t.dataset.deny) pendingRun = null; }
    if (t.dataset.exportRun) {
      const bundle = await post("/v1/ops/evidence/export", {run_id: t.dataset.exportRun});
      const response = await fetch(bundle.path, {headers: headers()});
      if (!response.ok) throw new Error("Evidence download failed");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a"); link.href = url; link.download = bundle.filename; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      showToast(`Exported ${bundle.filename}`);
    }
    if (t.id === "iv-create") {
      const value = await post("/v1/commissioning/interviews", {});
      sessionStorage.setItem("commissioning-interview", value.interview_id); await renderInterview();
    }
    if (t.id === "iv-template-load") {
      const {templates} = await get("/v1/commissioning/templates");
      const doc = templates[$("#iv-template").value];
      $("#iv-document").value = JSON.stringify(doc, null, 2);
      $("#iv-calibrations").value = JSON.stringify(doc.channels.map(c => ({calibration_id:c.calibration_id, reference:"SIMULATION_FIXTURE: template values, not physical calibration"})), null, 2);
    }
    if (["iv-save", "iv-propose", "iv-apply"].includes(t.id)) {
      const current = $("#interview-ui")._interview;
      const base = `/v1/commissioning/interviews/${current.interview_id}`;
      if (t.id === "iv-save") {
        const source = $("#iv-source").value.trim();
        const answers = {equipment:$("#iv-equipment").value.trim(), safe_state:$("#iv-safe").value, procedures:$("#iv-procedures").value.split(",").map(s => s.trim()).filter(Boolean), document:JSON.parse($("#iv-document").value), calibration_records:JSON.parse($("#iv-calibrations").value)};
        await post(base + "/answers", {expected_revision:current.revision, answers, sources:source ? Object.fromEntries(Object.keys(answers).map(k => [k, source])) : {}, text:$("#iv-text").value});
        await renderInterview();
      } else if (t.id === "iv-propose") {
        await post(base + "/propose", {}); await renderInterview();
      } else {
        await post("/v1/rig/apply", {document:current.proposal.document, expected_current_hash:current.proposal.current_hash, interview_id:current.interview_id, interview_revision:current.revision});
        await refreshContract(); await renderOnboard();
      }
    }
    if (t.id === "commission-review") {
      await post("/v1/commissioning/review", {expected_config_hash: $("#view-onboard").dataset.hash, procedure_ids: [$("#commission-procedure").value]});
      await renderOnboard();
    }
    if (t.id === "onboard-json-propose" || t.id === "onboard-json-apply") {
      const document = JSON.parse($("#onboard-document").value);
      const preview = await post("/v1/rig/propose", {document});
      $("#onboard-diff").textContent = `${preview.diff.join("\n")}\nnext ${preview.next_hash}`;
      if (t.id === "onboard-json-apply") {
        await post("/v1/rig/apply", {document, expected_current_hash: preview.current_hash});
        await refreshContract(); await renderOnboard();
      }
    }
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
    if (t.id === "onboard-propose" || t.id === "onboard-apply") {
      const current = $("#view-onboard")._document;
      if (!current) throw new Error("no writable rig document on this node");
      const next = structuredClone(current);
      document.querySelectorAll("#onboard-channels input").forEach((input) => {
        const row = next.channels[Number(input.dataset.ch)];
        if (!row) return;
        const field = input.dataset.field;
        row[field] = input.type === "number" ? Number(input.value) : input.value;
      });
      const preview = await post("/v1/rig/propose", { document: next });
      $("#onboard-diff").textContent = `${(preview.diff || []).join("\n")}\nnext ${preview.next_hash}`;
      if (t.id === "onboard-apply") {
        await post("/v1/rig/apply", { document: next, expected_current_hash: preview.current_hash });
        showToast("Rig config applied");
        await renderOnboard();
      }
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
  const current = document.querySelector(".view:not(.hidden)")?.dataset.view;
  if (name !== current) activate(name);
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

document.body.addEventListener("change", async event => {
  if (event.target.id === "iv-resume") {
    sessionStorage.setItem("commissioning-interview", event.target.value);
    try { await renderInterview(); } catch (error) { fail(error); }
  }
});
