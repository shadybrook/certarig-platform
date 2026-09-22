export function gaugeMarkup({
  kind,
  label,
  value,
  unit,
  state,
  tone,
  deg,
  valueId,
  needle,
  hot = false,
  maxLabel = "high",
}) {
  const valueHtml = valueId
    ? `<strong id="${valueId}">${value}</strong><span>${unit}</span>`
    : `<strong>${value}</strong><span>${unit}</span>`;
  const needleAttrs = needle
    ? `class="gauge-needle" data-needle="${needle}" transform="rotate(${deg} 70 78)"`
    : `class="gauge-needle" transform="rotate(${deg} 70 78)"`;
  return `
    <article class="gauge" data-kind="${kind}" data-tone="${tone}">
      <svg viewBox="0 0 140 108" aria-hidden="true">
        <path class="gauge-track" d="M20 78 A 50 50 0 0 1 120 78" fill="none" />
        ${
          hot
            ? `<path class="gauge-hot" d="M98 32 A 50 50 0 0 1 120 78" fill="none" />`
            : ""
        }
        <g ${needleAttrs}>
          <line x1="70" y1="78" x2="70" y2="32" />
          <circle cx="70" cy="78" r="5" />
        </g>
        <text class="gauge-tick" x="16" y="100">0</text>
        <text class="gauge-tick" x="124" y="100" text-anchor="end">${maxLabel}</text>
      </svg>
      <p class="gauge-value">${valueHtml}</p>
      <p class="gauge-name">${label}</p>
      <p class="gauge-state">${state}</p>
    </article>
  `;
}

export function stationMarkup(opts = {}) {
  const pressure = gaugeMarkup({
    kind: "pressure",
    label: "Pressure",
    value: opts.pressure ?? "1.16",
    unit: "bar",
    state: "high",
    tone: "high",
    deg: 42,
    valueId: opts.pressureId,
    needle: opts.needles ? "pressure" : undefined,
    hot: true,
    maxLabel: "high",
  });
  const flow = gaugeMarkup({
    kind: "flow",
    label: "Flow",
    value: opts.flow ?? "0.21",
    unit: "L/min",
    state: "held",
    tone: "held",
    deg: -38,
    valueId: opts.flowId,
    needle: opts.needles ? "flow" : undefined,
    hot: false,
    maxLabel: "max",
  });
  return `
    <div class="station-card">
      <p class="station-kicker">Small test station</p>
      <div class="gauges">${pressure}${flow}</div>
      <svg class="station-rig" viewBox="0 0 360 86" aria-hidden="true">
        <path class="pipe" d="M90 0 v26 H180 v12" />
        <path class="pipe" d="M270 0 v26 H180" />
        <rect class="vessel" x="148" y="38" width="64" height="30" rx="12" />
        <text x="180" y="57" text-anchor="middle">test vessel</text>
        <rect class="bench" x="36" y="76" width="288" height="6" rx="2" />
      </svg>
    </div>
  `;
}

const STORY = [
  ["run", "Output on"],
  ["trip", "Output off"],
  ["healthy", "Healthy, still off"],
  ["reset", "Reset"],
  ["permit", "Permit → on"],
];

export function checkerMarkup({
  on = false,
  permit = false,
  estop = true,
  healthy = false,
  latched = true,
  controls = false,
  story = false,
} = {}) {
  return `
    <div class="checker-panel">
      <div class="checker-top">
        <span>Checker</span>
        <span class="chrome-out">${on ? "On" : "Off"}</span>
      </div>
      <div class="checker-board">
        <div class="out-switch" data-on="${on}" data-lock="${latched}">
          <span class="bulb" aria-hidden="true"></span>
          <strong class="out-word">${on ? "On" : "Off"}</strong>
          <span class="out-label">Output</span>
          <em class="out-note"></em>
        </div>
        <ul class="checks">
          <li data-check="permit" data-ok="${permit}"><span>Permit</span><b>${permit ? "on" : "off"}</b></li>
          <li data-check="estop" data-ok="${estop}"><span>E-stop</span><b>${estop ? "closed" : "open"}</b></li>
          <li data-check="reading" data-ok="${healthy}"><span>Reading</span><b>${healthy ? "healthy" : "high"}</b></li>
        </ul>
        ${
          story
            ? `<ol class="latch-story">${STORY.map(
                ([id, label]) => `<li data-story="${id}">${label}</li>`,
              ).join("")}</ol>`
            : ""
        }
        ${
          controls
            ? `
          <div class="kernel-controls">
            <button class="term-toggle" type="button" data-act="healthy" aria-pressed="${healthy}">Reading: ${healthy ? "healthy" : "high"}</button>
            <button class="term-toggle" type="button" data-act="estop" aria-pressed="${estop}">E-stop: ${estop ? "closed" : "open"}</button>
            <button type="button" data-act="reset" disabled>Reset</button>
            <button class="primary" type="button" data-act="permit" disabled>Permit</button>
          </div>
          <p class="status-line" aria-live="polite"></p>
        `
            : ""
        }
      </div>
    </div>
  `;
}

export function outputOf(s) {
  return s.outputAllowed && s.permit && !s.tripLatched && s.estopClosed && s.healthy;
}

export function storyOf(s) {
  if (s.story) return s.story;
  if (s.tripLatched && !s.healthy) return "trip";
  if (s.tripLatched) return "healthy";
  if (!outputOf(s) && !s.permit) return "reset";
  if (outputOf(s)) return "permit";
  return "run";
}

export function paintChecker(root, s) {
  const on = outputOf(s);
  const story = storyOf(s);
  const lamp = root.querySelector(".out-switch");
  if (lamp) {
    lamp.dataset.on = String(on);
    lamp.dataset.lock = String(Boolean(s.tripLatched));
    lamp.dataset.story = story;
  }
  const word = root.querySelector(".out-word");
  if (word) word.textContent = on ? "On" : "Off";
  const chrome = root.querySelector(".chrome-out");
  if (chrome) chrome.textContent = on ? "On" : "Off";
  const note = root.querySelector(".out-note");
  if (note) {
    note.textContent =
      s.tripLatched && s.healthy ? "Stays off" : !on && !s.tripLatched && s.healthy ? "Needs permit" : "";
  }

  const permit = root.querySelector('[data-check="permit"]');
  if (permit) {
    permit.dataset.ok = String(s.permit);
    permit.querySelector("b").textContent = s.permit ? "on" : "off";
  }
  const estop = root.querySelector('[data-check="estop"]');
  if (estop) {
    estop.dataset.ok = String(s.estopClosed);
    estop.querySelector("b").textContent = s.estopClosed ? "closed" : "open";
  }
  const reading = root.querySelector('[data-check="reading"]');
  if (reading) {
    reading.dataset.ok = String(s.healthy);
    reading.querySelector("b").textContent = s.healthy ? "healthy" : "high";
  }

  root.querySelectorAll(".latch-story [data-story]").forEach((li) => {
    li.setAttribute("aria-current", li.dataset.story === story ? "true" : "false");
  });

  const healthyBtn = root.querySelector('[data-act="healthy"]');
  if (healthyBtn) {
    healthyBtn.textContent = `Reading: ${s.healthy ? "healthy" : "high"}`;
    healthyBtn.setAttribute("aria-pressed", String(s.healthy));
  }
  const estopBtn = root.querySelector('[data-act="estop"]');
  if (estopBtn) {
    estopBtn.textContent = `E-stop: ${s.estopClosed ? "closed" : "open"}`;
    estopBtn.setAttribute("aria-pressed", String(s.estopClosed));
  }
  const resetOk = s.tripLatched && s.healthy && s.estopClosed;
  const permitOk = !s.tripLatched && s.healthy && s.estopClosed && s.outputAllowed && !s.permit;
  const reset = root.querySelector('[data-act="reset"]');
  const permitBtn = root.querySelector('[data-act="permit"]');
  if (reset) reset.disabled = !resetOk;
  if (permitBtn) permitBtn.disabled = !permitOk;
  const status = root.querySelector(".status-line");
  if (status && s.note != null) status.textContent = s.note;
  return on;
}
