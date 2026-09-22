import { tickCopy } from "../scroll.js";
import { checkerMarkup, paintChecker, outputOf } from "./bench.js";

function glossOf(s) {
  if (s.tripLatched && (!s.healthy || !s.estopClosed)) return "The model does not get a vote.";
  if (s.tripLatched && s.healthy && s.estopClosed) return "Health does not restart it.";
  if (!s.tripLatched && !s.permit && s.healthy && s.estopClosed && s.outputAllowed) {
    return "Reset, then permit.";
  }
  return "";
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
    story: "run",
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
    story: "trip",
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
    story: "healthy",
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
    story: "reset",
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
    story: "permit",
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
    story: BEATS[0].story,
  };
  let holdUntil = 0;
  let lastBeat = null;
  const title = document.getElementById("kernel-title");
  const gloss = document.getElementById("kernel-gloss");

  function trip(why) {
    state.tripLatched = true;
    state.permit = false;
    state.note = why;
  }

  function apply(extra = {}) {
    Object.assign(state, extra);
    paintChecker(el, state);
    if (gloss) {
      const line = glossOf(state);
      if (gloss.textContent !== line) {
        gloss.textContent = line;
        gloss.classList.toggle("is-on", Boolean(line));
        if (line) {
          gloss.classList.remove("tick");
          void gloss.offsetWidth;
          gloss.classList.add("tick");
        }
      }
    }
  }

  el.innerHTML = checkerMarkup({
    on: true,
    permit: true,
    estop: true,
    healthy: true,
    latched: false,
    controls: true,
    story: true,
  });

  el.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    if (!btn || btn.disabled) return;
    holdUntil = Date.now() + 1600;
    const act = btn.dataset.act;
    if (act === "healthy") {
      if (state.healthy) {
        state.healthy = false;
        trip("Latched.");
      } else {
        state.healthy = true;
        state.note = "Still latched.";
      }
      state.story = "";
    } else if (act === "estop") {
      if (state.estopClosed) {
        state.estopClosed = false;
        trip("E-stop open.");
      } else {
        state.estopClosed = true;
        state.note = "Still latched.";
      }
      state.story = "";
    } else if (act === "reset") {
      state.tripLatched = false;
      state.permit = false;
      state.note = "Need permit.";
      state.story = "reset";
    } else if (act === "permit") {
      state.permit = true;
      state.note = "Yes.";
      state.story = "permit";
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
        story: b.story,
      });
      tickCopy(title, b.title);
    },
    holding: () => Date.now() < holdUntil,
    output: () => outputOf(state),
  };
}
