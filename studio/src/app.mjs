import { evaluateScenario, listScenarios, safetyPolicy } from "./engine.mjs";

const select = document.querySelector("#scenario");
const runButton = document.querySelector("#run-analysis");
const exportButton = document.querySelector("#export-report");
const announcement = document.querySelector("#announcement");
const caseSelector = document.querySelector("#case-selector");
const workspace = document.querySelector(".demo-workspace");

const scenarios = listScenarios();

for (const scenario of scenarios) {
  const option = document.createElement("option");
  option.value = scenario.id;
  option.textContent = scenario.title;
  select.append(option);
}

function caseIndex(id) {
  return scenarios.findIndex(scenario => scenario.id === id) + 1;
}

function renderCaseSelector() {
  caseSelector.innerHTML = scenarios
    .map((scenario, index) => {
      const result = evaluateScenario(scenario.id);
      return `
        <button class="case-tab" type="button" data-case-id="${escapeHtml(scenario.id)}" data-tone="${escapeHtml(result.status.tone)}" aria-pressed="${scenario.id === select.value}">
          <span class="case-tab-number">0${index + 1}</span>
          <span class="case-tab-copy"><strong>${escapeHtml(scenario.title.replace(/^Case \d+: /, ""))}</strong><small>${escapeHtml(scenario.summary)}</small></span>
          <span class="case-tab-status">${escapeHtml(result.status.label)}</span>
        </button>`;
    })
    .join("");

  for (const button of caseSelector.querySelectorAll(".case-tab")) {
    button.addEventListener("click", () => {
      select.value = button.dataset.caseId;
      updateSelectedCase(button.dataset.caseId);
      announcement.textContent = `${button.textContent.trim()} selected. Run the analysis to update the decision workspace.`;
    });
  }
}

function updateSelectedCase(id) {
  for (const button of caseSelector.querySelectorAll(".case-tab")) {
    button.setAttribute("aria-pressed", String(button.dataset.caseId === id));
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function chartPath(values, width, left, right, top, bottom, min, max) {
  return values
    .map((value, index) => {
      const x = left + index / (values.length - 1) * (width - left - right);
      const y = bottom - (value - min) / (max - min) * (bottom - top);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function renderTelemetry(result) {
  const width = 760;
  const height = 360;
  const left = 48;
  const right = 20;
  const pressure = result.telemetry.map(row => row.pressure);
  const flow = result.telemetry.map(row => row.flow);
  const pressureMax = Math.max(7, Math.ceil(Math.max(...pressure)));
  const flowMax = Math.max(20, Math.ceil(Math.max(...flow)));
  const pressureTop = 42;
  const pressureBottom = 158;
  const flowTop = 226;
  const flowBottom = 326;
  const pressurePath = chartPath(pressure, width, left, right, pressureTop, pressureBottom, 0, pressureMax);
  const flowPath = chartPath(flow, width, left, right, flowTop, flowBottom, 0, flowMax);
  const limitY = pressureBottom - safetyPolicy.pressureLimitBar / pressureMax * (pressureBottom - pressureTop);
  const breachIndex = pressure.findIndex(value => value > safetyPolicy.pressureLimitBar);
  const breach = breachIndex >= 0 ? result.telemetry[breachIndex] : null;
  const breachX = breachIndex >= 0 ? left + breachIndex / (pressure.length - 1) * (width - left - right) : 0;
  const breachY = breach ? pressureBottom - breach.pressure / pressureMax * (pressureBottom - pressureTop) : 0;
  document.querySelector("#telemetry-chart").innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Pressure and flow telemetry for the selected case">
      <defs>
        <linearGradient id="pressure-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#24755c" stop-opacity=".24"/><stop offset="1" stop-color="#24755c" stop-opacity="0"/></linearGradient>
        <linearGradient id="flow-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#436b9f" stop-opacity=".18"/><stop offset="1" stop-color="#436b9f" stop-opacity="0"/></linearGradient>
      </defs>
      <rect x="${left}" y="${pressureTop}" width="${width - left - right}" height="${Math.max(0, limitY - pressureTop).toFixed(1)}" rx="8" class="danger-zone" />
      <line x1="${left}" x2="${width - right}" y1="${pressureTop}" y2="${pressureTop}" class="grid-line" />
      <line x1="${left}" x2="${width - right}" y1="${pressureBottom}" y2="${pressureBottom}" class="grid-line" />
      <text x="${left}" y="24" class="axis-title">Pressure</text><text x="${width - right}" y="24" text-anchor="end" class="axis-unit">bar</text>
      <text x="${left - 10}" y="${pressureTop + 4}" text-anchor="end" class="axis-label">${pressureMax}</text>
      <text x="${left - 10}" y="${pressureBottom + 4}" text-anchor="end" class="axis-label">0</text>
      <line x1="${left}" x2="${width - right}" y1="${limitY.toFixed(1)}" y2="${limitY.toFixed(1)}" class="limit-line" />
      <text x="${left + 8}" y="${Math.max(pressureTop + 13, limitY - 8).toFixed(1)}" class="limit-label">4.20 bar safety limit</text>
      <path d="${pressurePath} L${width - right},${pressureBottom} L${left},${pressureBottom} Z" class="series-area pressure-area" />
      <path d="${pressurePath}" class="series pressure" />
      ${breach ? `<circle cx="${breachX.toFixed(1)}" cy="${breachY.toFixed(1)}" r="6" class="event-marker"/><text x="${Math.min(width - 130, breachX + 12).toFixed(1)}" y="${Math.max(pressureTop + 16, breachY - 10).toFixed(1)}" class="event-label">Abort at ${breach.time.toFixed(1)} s</text>` : ""}

      <line x1="${left}" x2="${width - right}" y1="${flowTop}" y2="${flowTop}" class="grid-line" />
      <line x1="${left}" x2="${width - right}" y1="${flowBottom}" y2="${flowBottom}" class="grid-line" />
      <text x="${left}" y="208" class="axis-title">Flow</text><text x="${width - right}" y="208" text-anchor="end" class="axis-unit">L/min</text>
      <text x="${left - 10}" y="${flowTop + 4}" text-anchor="end" class="axis-label">${flowMax}</text>
      <text x="${left - 10}" y="${flowBottom + 4}" text-anchor="end" class="axis-label">0</text>
      <path d="${flowPath} L${width - right},${flowBottom} L${left},${flowBottom} Z" class="series-area flow-area" />
      <path d="${flowPath}" class="series flow" />
      <text x="${left}" y="350" class="axis-label">0 s</text>
      <text x="${width - right}" y="350" text-anchor="end" class="axis-label">12 s</text>
    </svg>`;
}

function decisionPath(result) {
  const mappingReview = result.findings.some(finding => finding.code === "MAPPING_CHANGED");
  const evidenceMissing = result.findings.some(finding => finding.code === "CALIBRATION_MISSING");
  const safeAbort = result.findings.some(finding => finding.code === "SAFE_LIMIT_EXCEEDED");
  return [
    { label: "Ingest", detail: "Configuration and calibration loaded", state: "complete", stateLabel: "Ready" },
    { label: "Compare", detail: evidenceMissing ? "Required calibration is missing" : mappingReview ? "Channel mapping conflict found" : "Baseline and proposal agree", state: evidenceMissing ? "blocked" : mappingReview ? "review" : "complete", stateLabel: evidenceMissing ? "Blocked" : mappingReview ? "Review" : "Matched" },
    { label: "Policy", detail: safeAbort ? "Pressure exceeds the approved limit" : evidenceMissing || mappingReview ? "Prerequisite prevents execution" : "Prerequisites and limits valid", state: safeAbort ? "abort" : evidenceMissing ? "blocked" : mappingReview ? "review" : "complete", stateLabel: safeAbort ? "Abort" : evidenceMissing || mappingReview ? "Held" : "Valid" },
    { label: "Runtime", detail: safeAbort ? "Output returned to its safe state" : evidenceMissing || mappingReview ? "Bounded plan was not armed" : "Five bounded steps completed", state: safeAbort ? "abort" : evidenceMissing || mappingReview ? "held" : "complete", stateLabel: safeAbort ? "Safe" : evidenceMissing || mappingReview ? "Not run" : "Complete" },
    { label: "Record", detail: "Decision and evidence checksum retained", state: "complete", stateLabel: "Saved" }
  ];
}

function renderDecisionPath(result) {
  document.querySelector("#decision-path").innerHTML = decisionPath(result)
    .map((step, index) => `
      <li data-state="${escapeHtml(step.state)}">
        <span class="decision-index">0${index + 1}</span>
        <span class="decision-copy"><strong>${escapeHtml(step.label)}</strong><small>${escapeHtml(step.detail)}</small></span>
        <span class="decision-state">${escapeHtml(step.stateLabel)}</span>
      </li>`)
    .join("");
}

function renderChannels(result) {
  document.querySelector("#channel-table tbody").innerHTML = result.channels
    .map(channel => `
      <tr>
        <td><strong>${escapeHtml(channel.id)}</strong></td>
        <td>${escapeHtml(channel.device)}</td>
        <td>${escapeHtml(channel.unit)}</td>
        <td>${escapeHtml(channel.calibration ?? "Missing")}</td>
        <td><span class="confidence">${Math.round(channel.confidence * 100)}%</span></td>
      </tr>`)
    .join("");
}

function renderFindings(result) {
  const container = document.querySelector("#findings");
  if (!result.findings.length) {
    container.innerHTML = '<li class="finding success"><strong>No material conflicts</strong><span>The baseline evidence and measured response agree.</span></li>';
    return;
  }
  container.innerHTML = result.findings
    .map(finding => `
      <li class="finding ${escapeHtml(finding.severity)}">
        <strong>${escapeHtml(finding.code)}</strong>
        <span>${escapeHtml(finding.message)}</span>
      </li>`)
    .join("");
}

function renderPlan(result) {
  document.querySelector("#plan").innerHTML = result.plan.steps
    .map(step => `
      <li>
        <span class="step-id">${escapeHtml(step.id)}</span>
        <span>${escapeHtml(step.action)}</span>
        <span class="step-status ${escapeHtml(step.status.replace(" ", "_"))}">${escapeHtml(step.status)}</span>
      </li>`)
    .join("");
  document.querySelector("#abort-rule").textContent = result.plan.abortRule;
}

function renderResult(result) {
  document.querySelector("#case-number").textContent = `0${caseIndex(result.id)}`;
  document.querySelector("#case-title").textContent = result.title;
  document.querySelector("#case-summary").textContent = result.summary;
  const status = document.querySelector("#status");
  status.textContent = result.status.label;
  status.dataset.tone = result.status.tone;
  document.querySelector("#metric-channels").textContent = result.metrics.channels;
  document.querySelector("#metric-confidence").textContent = `${result.metrics.confidence}%`;
  document.querySelector("#metric-findings").textContent = result.metrics.findings;
  document.querySelector("#metric-pressure").textContent = `${result.metrics.maxPressure.toFixed(2)} bar`;
  document.querySelector("#bundle-checksum").textContent = result.evidenceBundle.checksum;
  document.querySelector("#bundle-records").textContent = result.evidenceBundle.records;
  renderTelemetry(result);
  renderDecisionPath(result);
  renderChannels(result);
  renderFindings(result);
  renderPlan(result);
  announcement.textContent = `${result.title} complete. Outcome: ${result.status.label}.`;
  document.documentElement.dataset.scenario = result.id;
  updateSelectedCase(result.id);
  window.certarigResult = result;
}

function downloadResult(result) {
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `certarig-${result.id}-evidence.json`;
  link.click();
  URL.revokeObjectURL(url);
}

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  workspace.dataset.running = "true";
  runButton.lastChild.textContent = "Checking evidence…";
  await new Promise(resolve => setTimeout(resolve, 650));
  renderResult(evaluateScenario(select.value));
  runButton.lastChild.textContent = "Run analysis";
  workspace.dataset.running = "false";
  runButton.disabled = false;
});
select.addEventListener("change", () => {
  updateSelectedCase(select.value);
  announcement.textContent = `${select.options[select.selectedIndex].textContent} selected. Run the analysis to update the decision workspace.`;
});
exportButton.addEventListener("click", () => downloadResult(window.certarigResult));

renderCaseSelector();
renderResult(evaluateScenario("normal"));
