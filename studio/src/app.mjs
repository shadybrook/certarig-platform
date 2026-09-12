import { get, post, refreshContract, store } from "./api.mjs";

const $ = (sel) => document.querySelector(sel);
const views = [...document.querySelectorAll(".view")];
const toast = $("#toast");
let health = {};
let state = {};
let sessionId = null;
let poll = null;

function showToast(message, bad = false) {
  toast.textContent = message;
  toast.classList.toggle("hidden", false);
  toast.style.borderColor = bad ? "var(--bad)" : "var(--line)";
  setTimeout(() => toast.classList.add("hidden"), 4000);
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
    await refreshContract();
    health = await get("/health");
    gate(false);
    startPolling();
    render();
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
      $("#health-pill").dataset.state = "ok";
      $("#health-pill").textContent = `${health.hardware_mode} · ${health.rig_id}`;
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

function chart(history, key, max) {
  const pts = (history || []).map((row, i) => {
    const sample = (row.samples || []).find((s) => s.channel_id.includes(key) || s.concept === key);
    const value = sample ? Number(sample.value) : 0;
    return [i, value];
  });
  if (pts.length < 2) return "<p class='muted'>Waiting for samples…</p>";
  const w = 640, h = 160, top = 8, bot = 150;
  const path = pts
    .map(([i, v], n) => {
      const x = (i / (pts.length - 1)) * w;
      const y = bot - (Math.min(v, max) / max) * (bot - top);
      return `${n ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" aria-label="${key} chart"><path d="${path}" fill="none" stroke="#3d8bfd" stroke-width="2"/></svg>`;
}

function renderTelemetry() {
  const samples = state.samples || [];
  const g = state.guardrail || {};
  const cards = samples
    .map((s) => {
      const max = s.channel_id.includes("pressure") ? 10 : 20;
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
              <input type="range" min="0" max="${s.channel_id.includes("pressure") ? 10 : 20}" step="0.05"
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
      <article class="card">
        <p class="eyebrow">Guardrail</p>
        <strong id="guardrail-reason">${esc(g.reason)}</strong>
        <p>E-stop ${g.estop_active ? "ACTIVE" : "released"} · trip ${g.trip_latched ? "latched" : "clear"}</p>
        <p>Output <strong id="output-state">${state.outputs?.gpio23_command_high ? "HIGH" : "off"}</strong></p>
      </article>
      ${cards}
    </div>
    ${chart(state.history, "pressure", 6)}
    <div class="card" style="margin-top:12px">
      <button id="cmd-safe" class="danger" type="button">Force safe</button>
      <button id="cmd-reset" type="button">Reset trip</button>
      <button id="cmd-permit" class="primary" type="button">Request permit</button>
    </div>
    ${sim}`;
}

async function renderProcedures() {
  const [library, runs] = await Promise.all([get("/v1/procedures"), get("/v1/procedure_runs")]);
  const active = (runs.runs || []).find((r) => !r.terminal) || (runs.runs || [])[0];
  const detail = active ? await get(`/v1/procedure_runs/${active.run_id}`) : null;
  const list = (library.procedures || [])
    .map(
      (p) => `<option value="${esc(p.id)}">${esc(p.title || p.id)}</option>`
    )
    .join("");
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

function renderAgent() {
  if ($("#agent-log")) return;
  $("#view-agent").innerHTML = `
    <h1>Agent</h1>
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

async function renderOnboard() {
  const [rig, caps] = await Promise.all([get("/v1/rig"), get("/v1/capabilities")]);
  const mode = rig.rig.hardware.mode;
  const adapters = ["mock", "simulator", "raspberry_pi", "mqtt", "modbus_tcp", "opcua"];
  $("#view-onboard").innerHTML = `
    <h1>Onboard this rig</h1>
    <div class="card">
      <p class="eyebrow">1 · Connect</p>
      <p>Node ${esc(rig.rig.rig_id)} revision ${esc(rig.rig.revision)}</p>
    </div>
    <div class="card">
      <p class="eyebrow">2 · Interface</p>
      <div class="adapters">${adapters
        .map((a) => `<span class="${a === mode ? "on" : ""}">${esc(a)}${a === mode ? " (active)" : a === "mqtt" || a === "modbus_tcp" || a === "opcua" ? " — roadmap" : ""}</span>`)
        .join("")}</div>
    </div>
    <div class="card">
      <p class="eyebrow">3 · Signals</p>
      <table><thead><tr><th>Channel</th><th>Concept</th><th>Source</th><th>Trip</th></tr></thead>
      <tbody>${(rig.signals || [])
        .map(
          (s) => `<tr><td>${esc(s.channel_id)}</td><td>${esc(s.concept)}</td><td>${esc(s.source_id)}</td>
          <td>${esc(JSON.stringify(s.limits?.trip || s.limits?.valid || []))}</td></tr>`
        )
        .join("")}</tbody></table>
    </div>
    <div class="card">
      <p class="eyebrow">4 · Capabilities</p>
      <p>${esc(caps.description || caps.manifest_id)}</p>
    </div>`;
}

async function render() {
  const name = document.querySelector(".view:not(.hidden)")?.dataset.view || "telemetry";
  try {
    if (name === "telemetry") renderTelemetry();
    else if (name === "procedures") await renderProcedures();
    else if (name === "approvals") await renderApprovals();
    else if (name === "agent") renderAgent();
    else if (name === "evidence") await renderEvidence();
    else if (name === "capabilities") await renderCapabilities();
    else if (name === "onboard") await renderOnboard();
  } catch (error) {
    showToast(error.message, true);
  }
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
      await post("/v1/procedure_runs", { procedure_id: id });
      activate("procedures");
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
    if (t.id === "logout") logout();
  } catch (error) {
    showToast(error.message, true);
  }
});

document.body.addEventListener("input", async (event) => {
  const t = event.target;
  if (t instanceof HTMLInputElement && t.dataset.channel) {
    try {
      await post("/v1/sim/set_target", { channel: t.dataset.channel, value: Number(t.value) });
    } catch (error) {
      showToast(error.message, true);
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
      const tools = (result.tool_calls || [])
        .map((c) => `${c.ok ? "ok" : "refused"} ${c.name}`)
        .join(" · ");
      log.insertAdjacentHTML(
        "beforeend",
        `<div class="bubble">${esc(result.text)}<div class="tools">${esc(tools)}</div></div>`
      );
      log.scrollTop = log.scrollHeight;
    } catch (error) {
      showToast(error.message, true);
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
  const name = location.hash.replace("#", "") || "telemetry";
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
    activate(location.hash.replace("#", "") || "telemetry");
  } catch {
    store.clear();
    gate(true);
  }
})();
