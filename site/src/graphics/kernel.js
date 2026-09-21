import { tickCopy } from "../scroll.js";

function outputOf(s) {
  return s.outputAllowed && s.permit && !s.tripLatched && s.estopClosed && s.healthy;
}

const BEATS = [
  {
    at: 0,
    outputAllowed: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "Yes.",
    title: "The model does not get a vote.",
  },
  {
    at: 0.22,
    outputAllowed: true,
    permit: false,
    tripLatched: true,
    estopClosed: true,
    healthy: false,
    note: "Latched.",
    title: "Break one check.",
  },
  {
    at: 0.44,
    outputAllowed: true,
    permit: false,
    tripLatched: true,
    estopClosed: true,
    healthy: true,
    note: "Still latched.",
    title: "Healthy is not a restart.",
  },
  {
    at: 0.64,
    outputAllowed: true,
    permit: false,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "Need permit.",
    title: "Reset. Then permit.",
  },
  {
    at: 0.84,
    outputAllowed: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "Yes.",
    title: "Only the kernel said yes.",
  },
];

function beatAt(p) {
  let b = BEATS[0];
  for (const n of BEATS) if (p >= n.at) b = n;
  return b;
}

export function renderKernel(el) {
  const state = {
    outputAllowed: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: BEATS[0].note,
  };
  let holdUntil = 0;
  let lastBeat = null;
  const title = document.getElementById("kernel-title");

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
      !state.tripLatched && state.healthy && state.estopClosed && state.outputAllowed && !state.permit;
    el.querySelector(".led").dataset.tone = on ? "ok" : "bad";
    el.querySelector(".chrome-out").textContent = on ? "ON" : "OFF";
    const rows = el.querySelectorAll(".and-term");
    const oks = [state.outputAllowed, state.permit, !state.tripLatched, state.estopClosed, state.healthy];
    rows.forEach((row, i) => row.setAttribute("data-ok", String(oks[i])));
    const lamp = el.querySelector(".out-lamp");
    lamp.dataset.on = String(on);
    el.querySelector(".lamp-copy").textContent = on ? "on" : "off";
    const bit = el.querySelector(".kernel-bit");
    bit.textContent = on ? "1" : "0";
    bit.parentElement.dataset.on = String(on);
    el.querySelector('[data-act="output"]').textContent = `Output: ${state.outputAllowed ? "allowed" : "held"}`;
    el.querySelector('[data-act="output"]').setAttribute("aria-pressed", String(state.outputAllowed));
    el.querySelector('[data-act="healthy"]').textContent = `Process: ${state.healthy ? "healthy" : "over limit"}`;
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
        <span>kernel</span>
        <span class="spacer chrome-out">ON</span>
      </div>
      <div class="instrument-face kernel-face">
        <div class="kernel-bit-wrap" data-on="true"><span class="kernel-bit">1</span><span>output</span></div>
        <div class="and-bus">
          <div class="and-term" data-ok="true"><span>output allowed</span><i></i></div>
          <div class="and-term" data-ok="true"><span>permit on</span><i></i></div>
          <div class="and-term" data-ok="true"><span>not tripped</span><i></i></div>
          <div class="and-term" data-ok="true"><span>e-stop closed</span><i></i></div>
          <div class="and-term" data-ok="true"><span>process healthy</span><i></i></div>
        </div>
        <div class="out-lamp" data-on="true"><span class="bulb"></span><span class="lamp-copy">on</span></div>
        <div class="kernel-controls">
          <button class="term-toggle" type="button" data-act="output" aria-pressed="true">Output: allowed</button>
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
    holdUntil = Date.now() + 1600;
    const act = btn.dataset.act;
    if (act === "output") {
      state.outputAllowed = !state.outputAllowed;
      if (!state.outputAllowed) {
        state.permit = false;
        state.note = "Held off.";
      } else {
        state.note = "Need permit.";
      }
    } else if (act === "healthy") {
      if (state.healthy) {
        state.healthy = false;
        trip("Latched.");
      } else {
        state.healthy = true;
        state.note = "Still latched.";
      }
    } else if (act === "estop") {
      if (state.estopClosed) {
        state.estopClosed = false;
        trip("E-stop open.");
      } else {
        state.estopClosed = true;
        state.note = "Still latched.";
      }
    } else if (act === "reset") {
      state.tripLatched = false;
      state.permit = false;
      state.note = "Need permit.";
    } else if (act === "permit") {
      state.permit = true;
      state.note = "Yes.";
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
        outputAllowed: b.outputAllowed,
        permit: b.permit,
        tripLatched: b.tripLatched,
        estopClosed: b.estopClosed,
        healthy: b.healthy,
        note: b.note,
      });
      tickCopy(title, b.title);
    },
    holding: () => Date.now() < holdUntil,
  };
}
