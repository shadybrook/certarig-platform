import { tickCopy } from "../scroll.js";

function outputOf(s) {
  return s.actuationEnabled && s.permit && !s.tripLatched && s.estopClosed && s.healthy;
}

const BEATS = [
  {
    at: 0,
    actuationEnabled: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "All five true. Kernel said yes.",
    title: "The model does not get a vote.",
    line: "Five terms. One output.",
  },
  {
    at: 0.22,
    actuationEnabled: true,
    permit: false,
    tripLatched: true,
    estopClosed: true,
    healthy: false,
    note: "Over-limit. Trip latched. Permit cleared.",
    title: "Break one term.",
    line: "Output is false.",
  },
  {
    at: 0.44,
    actuationEnabled: true,
    permit: false,
    tripLatched: true,
    estopClosed: true,
    healthy: true,
    note: "Healthy again. Still latched. No auto-restart.",
    title: "Healthy is not a restart.",
    line: "The latch holds.",
  },
  {
    at: 0.64,
    actuationEnabled: true,
    permit: false,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "Reset accepted. Awaiting a new permit.",
    title: "Reset. Then permit.",
    line: "A human owns the irreversible act.",
  },
  {
    at: 0.84,
    actuationEnabled: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "Permit requested. The kernel — not the agent — said yes.",
    title: "Only the kernel said yes.",
    line: "Language never crossed this panel.",
  },
];

function beatAt(p) {
  let b = BEATS[0];
  for (const n of BEATS) if (p >= n.at) b = n;
  return b;
}

export function renderKernel(el) {
  const state = {
    actuationEnabled: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: BEATS[0].note,
  };
  let holdUntil = 0;
  let lastBeat = null;
  const title = document.getElementById("kernel-title");
  const line = document.getElementById("kernel-line");

  function trip(why) {
    state.tripLatched = true;
    state.permit = false;
    state.note = why;
  }

  function apply(extra = {}) {
    Object.assign(state, extra);
    const on = outputOf(state);
    const resetOk = state.tripLatched && state.healthy && state.estopClosed;
    const permitOk =
      !state.tripLatched && state.healthy && state.estopClosed && state.actuationEnabled && !state.permit;
    el.querySelector(".led").dataset.tone = on ? "ok" : "bad";
    el.querySelector(".chrome-out").textContent = on ? "OUTPUT 1" : "OUTPUT 0";
    const rows = el.querySelectorAll(".and-term");
    const oks = [state.actuationEnabled, state.permit, !state.tripLatched, state.estopClosed, state.healthy];
    rows.forEach((row, i) => row.setAttribute("data-ok", String(oks[i])));
    const lamp = el.querySelector(".out-lamp");
    lamp.dataset.on = String(on);
    el.querySelector(".lamp-copy").textContent = on
      ? "Output true — kernel said yes."
      : "Output false — kernel said no.";
    const bit = el.querySelector(".kernel-bit");
    bit.textContent = on ? "1" : "0";
    bit.parentElement.dataset.on = String(on);
    el.querySelector('[data-act="actuation"]').textContent = `Actuation: ${state.actuationEnabled ? "enabled" : "held at 0"}`;
    el.querySelector('[data-act="actuation"]').setAttribute("aria-pressed", String(state.actuationEnabled));
    el.querySelector('[data-act="healthy"]').textContent = `Process: ${state.healthy ? "healthy" : "over-limit"}`;
    el.querySelector('[data-act="healthy"]').setAttribute("aria-pressed", String(state.healthy));
    el.querySelector('[data-act="estop"]').textContent = `E-stop: ${state.estopClosed ? "closed" : "open"}`;
    el.querySelector('[data-act="estop"]').setAttribute("aria-pressed", String(state.estopClosed));
    el.querySelector('[data-act="reset"]').disabled = !resetOk;
    el.querySelector('[data-act="permit"]').disabled = !permitOk;
    el.querySelector(".status-line").textContent = state.note;
  }

  el.innerHTML = `
    <div class="instrument">
      <div class="instrument-chrome">
        <span class="led" data-tone="ok"></span>
        <span>kernel · drive_high</span>
        <span class="spacer chrome-out">OUTPUT 1</span>
      </div>
      <div class="instrument-face kernel-face">
        <div class="kernel-bit-wrap" data-on="true"><span class="kernel-bit">1</span><span>drive_high</span></div>
        <div class="and-bus">
          <div class="and-term" data-ok="true"><span>actuation enabled</span><i></i></div>
          <div class="and-term" data-ok="true"><span>permit requested</span><i></i></div>
          <div class="and-term" data-ok="true"><span>trip not latched</span><i></i></div>
          <div class="and-term" data-ok="true"><span>emergency stop closed</span><i></i></div>
          <div class="and-term" data-ok="true"><span>process healthy</span><i></i></div>
        </div>
        <div class="out-lamp" data-on="true"><span class="bulb"></span><span class="lamp-copy">Output true — kernel said yes.</span></div>
        <div class="kernel-controls">
          <button class="term-toggle" type="button" data-act="actuation" aria-pressed="true">Actuation: enabled</button>
          <button class="term-toggle" type="button" data-act="healthy" aria-pressed="true">Process: healthy</button>
          <button class="term-toggle" type="button" data-act="estop" aria-pressed="true">E-stop: closed</button>
          <button type="button" data-act="reset" disabled>Reset trip</button>
          <button class="primary" type="button" data-act="permit" disabled>Request permit</button>
        </div>
        <p class="status-line" aria-live="polite">${state.note}</p>
      </div>
    </div>
  `;

  el.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    if (!btn || btn.disabled) return;
    holdUntil = Date.now() + 2500;
    const act = btn.dataset.act;
    if (act === "actuation") {
      state.actuationEnabled = !state.actuationEnabled;
      if (!state.actuationEnabled) {
        state.permit = false;
        state.note = "Actuation held at 0. Enabling is not a yes.";
      } else {
        state.note = "Actuation enabled. Still needs a permit.";
      }
    } else if (act === "healthy") {
      if (state.healthy) {
        state.healthy = false;
        trip("Over-limit. Trip latched. Returning to healthy will not restart it.");
      } else {
        state.healthy = true;
        state.note = "Healthy again. Still latched.";
      }
    } else if (act === "estop") {
      if (state.estopClosed) {
        state.estopClosed = false;
        trip("E-stop open. Forced safe. Release will not restore a permit.");
      } else {
        state.estopClosed = true;
        state.note = "E-stop closed. Still latched. Still no permit.";
      }
    } else if (act === "reset") {
      state.tripLatched = false;
      state.permit = false;
      state.note = "Reset accepted. Now a human may request a permit.";
    } else if (act === "permit") {
      state.permit = true;
      state.note = "Permit requested. The kernel said yes.";
    }
    apply();
  });

  apply();

  return {
    play(p) {
      if (Date.now() < holdUntil) return;
      const b = beatAt(p);
      if (b === lastBeat) return;
      lastBeat = b;
      apply({
        actuationEnabled: b.actuationEnabled,
        permit: b.permit,
        tripLatched: b.tripLatched,
        estopClosed: b.estopClosed,
        healthy: b.healthy,
        note: b.note,
      });
      tickCopy(title, b.title);
      if (line) line.textContent = b.line;
    },
    holding: () => Date.now() < holdUntil,
  };
}
