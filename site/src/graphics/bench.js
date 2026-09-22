export const GAUGE = {
  cx: 70,
  cy: 66,
  start: -135,
  sweep: 270,
};

export const PRESSURE = {
  kind: "pressure",
  label: "Pressure",
  unit: "bar",
  min: 0,
  max: 2,
  major: 0.5,
  minor: 0.1,
  zoneFrom: 1,
  zoneTo: 2,
  zoneTone: "high",
  inWord: "high",
  outWord: "ok",
};

export const FLOW = {
  kind: "flow",
  label: "Flow",
  unit: "L/min",
  min: 0,
  max: 1,
  major: 0.2,
  minor: 0.05,
  zoneFrom: 0,
  zoneTo: 0.35,
  zoneTone: "held",
  inWord: "held",
  outWord: "open",
};

export function needleDeg(value, min, max) {
  const t = Math.min(1, Math.max(0, (Number(value) - min) / (max - min)));
  return GAUGE.start + t * GAUGE.sweep;
}

export function gaugeState(spec, value) {
  const v = Number(value);
  const inZone = v >= spec.zoneFrom && v <= spec.zoneTo;
  return {
    word: inZone ? spec.inWord : spec.outWord,
    tone: inZone ? spec.zoneTone : "ok",
  };
}

function polar(deg, radius) {
  const a = (deg * Math.PI) / 180;
  return {
    x: GAUGE.cx + radius * Math.sin(a),
    y: GAUGE.cy - radius * Math.cos(a),
  };
}

function arcPath(radius, fromDeg, toDeg) {
  const a = polar(fromDeg, radius);
  const b = polar(toDeg, radius);
  const delta = toDeg - fromDeg;
  const large = Math.abs(delta) > 180 ? 1 : 0;
  const sweep = delta >= 0 ? 1 : 0;
  return `M${a.x.toFixed(2)} ${a.y.toFixed(2)} A${radius} ${radius} 0 ${large} ${sweep} ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
}

function ticksMarkup(spec) {
  const steps = Math.round((spec.max - spec.min) / spec.minor);
  let svg = "";
  for (let i = 0; i <= steps; i += 1) {
    const value = spec.min + i * spec.minor;
    const major = Math.abs(value / spec.major - Math.round(value / spec.major)) < 1e-6;
    const deg = needleDeg(value, spec.min, spec.max);
    const inner = polar(deg, major ? 42 : 46);
    const outer = polar(deg, 52);
    svg += `<line class="${major ? "tick-major" : "tick-minor"}" x1="${inner.x.toFixed(2)}" y1="${inner.y.toFixed(2)}" x2="${outer.x.toFixed(2)}" y2="${outer.y.toFixed(2)}" />`;
    if (major) {
      const n = polar(deg, 34);
      const label = Math.abs(value - Math.round(value)) < 1e-6 ? String(Math.round(value)) : value.toFixed(1);
      svg += `<text class="gauge-num" x="${n.x.toFixed(2)}" y="${n.y.toFixed(2)}" text-anchor="middle" dominant-baseline="middle">${label}</text>`;
    }
  }
  return svg;
}

export function gaugeMarkup(spec, rawValue, opts = {}) {
  const value = Number(rawValue);
  const shown = value.toFixed(2);
  const { word, tone } = gaugeState(spec, value);
  const deg = needleDeg(value, spec.min, spec.max);
  const zoneFrom = needleDeg(spec.zoneFrom, spec.min, spec.max);
  const zoneTo = needleDeg(spec.zoneTo, spec.min, spec.max);
  const readAttrs = opts.valueId ? `id="${opts.valueId}"` : "";
  return `
    <article class="gauge" data-kind="${spec.kind}" data-tone="${tone}">
      <p class="gauge-name">${spec.label}</p>
      <svg class="gauge-face" viewBox="0 0 140 168" aria-hidden="true">
        <circle class="gauge-ring" cx="${GAUGE.cx}" cy="${GAUGE.cy}" r="64" />
        <circle class="gauge-dial" cx="${GAUGE.cx}" cy="${GAUGE.cy}" r="56" />
        <circle class="gauge-lip" cx="${GAUGE.cx}" cy="${GAUGE.cy}" r="56.5" />
        <path class="gauge-track" d="${arcPath(51, GAUGE.start, GAUGE.start + GAUGE.sweep)}" fill="none" />
        <path class="gauge-zone" data-zone="${spec.zoneTone}" d="${arcPath(51, zoneFrom, zoneTo)}" fill="none" />
        ${ticksMarkup(spec)}
        <g class="gauge-needle" data-needle="${spec.kind}" transform="rotate(${deg.toFixed(2)} ${GAUGE.cx} ${GAUGE.cy})">
          <polygon points="${GAUGE.cx},${GAUGE.cy - 46} ${GAUGE.cx + 2.8},${GAUGE.cy + 9} ${GAUGE.cx},${GAUGE.cy + 14} ${GAUGE.cx - 2.8},${GAUGE.cy + 9}" />
          <circle class="gauge-hub" cx="${GAUGE.cx}" cy="${GAUGE.cy}" r="5.5" />
          <circle class="gauge-hub-pin" cx="${GAUGE.cx}" cy="${GAUGE.cy}" r="2.2" />
        </g>
        <text class="gauge-read" ${readAttrs} x="${GAUGE.cx}" y="100" text-anchor="middle">${shown}</text>
        <text class="gauge-unit" x="${GAUGE.cx}" y="111" text-anchor="middle">${spec.unit}</text>
        <text class="gauge-state" x="${GAUGE.cx}" y="122" text-anchor="middle">${word}</text>
        <rect class="gauge-nut" x="61" y="128" width="18" height="8" rx="1.2" />
        <rect class="gauge-stem" x="66" y="136" width="8" height="32" rx="1.2" />
      </svg>
    </article>
  `;
}

export function paintGauge(article, spec, value) {
  if (!article) return;
  const v = Number(value);
  const { word, tone } = gaugeState(spec, v);
  article.dataset.tone = tone;
  const read = article.querySelector(".gauge-read");
  if (read) read.textContent = v.toFixed(2);
  const state = article.querySelector(".gauge-state");
  if (state) state.textContent = word;
  const needle = article.querySelector(".gauge-needle");
  if (needle) {
    needle.setAttribute(
      "transform",
      `rotate(${needleDeg(v, spec.min, spec.max).toFixed(2)} ${GAUGE.cx} ${GAUGE.cy})`,
    );
  }
}

function plumbingMarkup() {
  return `
    <svg class="station-rig" viewBox="0 0 420 96" aria-hidden="true">
      <rect class="fitting" x="98" y="0" width="14" height="7" rx="1" />
      <rect class="fitting" x="308" y="0" width="14" height="7" rx="1" />
      <path class="pipe" d="M105 7 V30 H210 V50" />
      <path class="pipe" d="M315 7 V30 H210" />
      <circle class="fitting-tee" cx="210" cy="30" r="4" />
      <ellipse class="vessel-cap" cx="210" cy="58" rx="46" ry="9" />
      <rect class="vessel" x="164" y="58" width="92" height="22" />
      <ellipse class="vessel-cap" cx="210" cy="80" rx="46" ry="9" />
      <text x="210" y="73" text-anchor="middle">test vessel</text>
    </svg>
  `;
}

export function stationMarkup(opts = {}) {
  const pressure = opts.pressure ?? 1.16;
  const flow = opts.flow ?? 0.21;
  return `
    <div class="station-card">
      <p class="station-caption">This is the station. These are the numbers.</p>
      <div class="station-body">
        <div class="gauges">
          ${gaugeMarkup(PRESSURE, pressure, { valueId: opts.pressureId })}
          ${gaugeMarkup(FLOW, flow, { valueId: opts.flowId })}
        </div>
        ${plumbingMarkup()}
      </div>
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
