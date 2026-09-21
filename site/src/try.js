function outputOf(s) {
  return s.outputAllowed && s.permit && !s.tripLatched && s.estopClosed && s.healthy;
}

function glossOf(s) {
  if (s.tripLatched && (!s.healthy || !s.estopClosed)) return "The model does not get a vote.";
  if (s.tripLatched && s.healthy && s.estopClosed) return "Health does not restart it.";
  if (!s.tripLatched && !s.permit && s.healthy && s.estopClosed && s.outputAllowed) {
    return "Reset, then permit.";
  }
  return "";
}

const DEMO = "c1e0a94b7d2f18e6a0c35b91d47e82f0b6a19c4d8e27f53a10b8c6d4e9f20173";
const BEATS = ["watch", "ask", "checker", "zip"];
const SHEETS = [
  { name: "checksums", offset: 0 },
  { name: "manifest", offset: 10 },
  { name: "report", offset: 20 },
  { name: "log", offset: 30 },
  { name: "notes", offset: 48, notes: true },
];

function hexWalk(target, step) {
  const chars = "0123456789abcdef";
  return target
    .split("")
    .map((ch, i) => (i < step ? ch : chars[(i * 7 + step) % 16]))
    .join("");
}

function mountKernel(el, { title, gloss, onChange }) {
  const state = {
    outputAllowed: true,
    permit: false,
    tripLatched: true,
    estopClosed: true,
    healthy: false,
    note: "Latched.",
  };

  function apply(extra = {}) {
    Object.assign(state, extra);
    const on = outputOf(state);
    const resetOk = state.tripLatched && state.healthy && state.estopClosed;
    const permitOk =
      !state.tripLatched && state.healthy && state.estopClosed && state.outputAllowed && !state.permit;
    el.querySelector(".led").dataset.tone = on ? "ok" : "bad";
    el.querySelector(".chrome-out").textContent = on ? "ON" : "OFF";
    const oks = [state.outputAllowed, state.permit, !state.tripLatched, state.estopClosed, state.healthy];
    el.querySelectorAll(".and-term").forEach((row, i) => row.setAttribute("data-ok", String(oks[i])));
    el.querySelector(".out-lamp").dataset.on = String(on);
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
    const line = glossOf(state);
    if (gloss) {
      gloss.textContent = line;
      gloss.classList.toggle("is-on", Boolean(line));
    }
    if (title) {
      title.textContent = on ? "The checker said yes." : "The checker said no.";
    }
    onChange?.(on, state);
  }

  function trip(why) {
    state.tripLatched = true;
    state.permit = false;
    state.note = why;
  }

  el.innerHTML = `
    <div class="instrument">
      <div class="instrument-chrome">
        <span class="led" data-tone="bad"></span>
        <span>checker</span>
        <span class="spacer chrome-out">OFF</span>
      </div>
      <div class="instrument-face kernel-face">
        <div class="kernel-bit-wrap" data-on="false"><span class="kernel-bit">0</span><span>output</span></div>
        <div class="and-bus">
          <div class="and-term" data-ok="true"><span>output allowed</span><i></i></div>
          <div class="and-term" data-ok="false"><span>permit on</span><i></i></div>
          <div class="and-term" data-ok="false"><span>not tripped</span><i></i></div>
          <div class="and-term" data-ok="true"><span>e-stop closed</span><i></i></div>
          <div class="and-term" data-ok="false"><span>process healthy</span><i></i></div>
        </div>
        <div class="out-lamp" data-on="false"><span class="bulb"></span><span class="lamp-copy">off</span></div>
        <div class="kernel-controls">
          <button class="term-toggle" type="button" data-act="output" aria-pressed="true">Output: allowed</button>
          <button class="term-toggle" type="button" data-act="healthy" aria-pressed="false">Process: over limit</button>
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
    restoreHealth() {
      if (!state.healthy) {
        state.healthy = true;
        state.note = "Still latched.";
        apply();
      }
    },
  };
}

function mountZip(el) {
  el.innerHTML = `
    <div class="instrument">
      <div class="instrument-chrome">
        <span class="led" data-tone="gold"></span>
        <span>evidence zip</span>
        <span class="spacer">rehash</span>
      </div>
      <div class="instrument-face zip-face">
        <div class="zip-stack">
          ${SHEETS.map(
            (s) => `
              <div class="zip-sheet${s.notes ? " narrative" : ""}" style="--offset:${s.offset}px">
                <span>${s.name}</span>
              </div>`,
          ).join("")}
        </div>
        <div class="zip-actions">
          <button type="button" data-rehash>Rehash</button>
          <span class="rehash-out" aria-live="polite"></span>
        </div>
      </div>
    </div>
  `;
  const nodes = [...el.querySelectorAll(".zip-sheet")];
  const out = el.querySelector(".rehash-out");
  const btn = el.querySelector("[data-rehash]");
  let timer = 0;

  function rehash() {
    window.clearInterval(timer);
    let step = 0;
    btn.disabled = true;
    timer = window.setInterval(() => {
      step += 4;
      out.textContent = hexWalk(DEMO, step);
      if (step >= 64) {
        window.clearInterval(timer);
        out.textContent = "Match.";
        btn.disabled = false;
      }
    }, 24);
  }

  btn.addEventListener("click", rehash);
  return {
    play() {
      nodes.forEach((node) => {
        node.classList.add("in");
        node.style.transform = "none";
      });
      rehash();
    },
  };
}

const unlocked = new Set(["watch"]);
let current = "watch";
let healthTimer = 0;

const kernel = mountKernel(document.querySelector("#try-kernel"), {
  title: document.getElementById("try-kernel-title"),
  gloss: document.getElementById("try-kernel-gloss"),
  onChange(on) {
    const take = document.querySelector('[data-next="zip"]');
    if (take) take.disabled = !on;
    if (on) unlocked.add("zip");
    syncRail();
  },
});
const zip = mountZip(document.querySelector("#try-zip"));

function syncRail() {
  document.querySelectorAll(".try-rail button").forEach((btn) => {
    const beat = btn.dataset.beat;
    btn.disabled = !unlocked.has(beat);
    btn.setAttribute("aria-current", beat === current ? "true" : "false");
  });
}

function show(beat) {
  if (!BEATS.includes(beat) || !unlocked.has(beat)) return;
  current = beat;
  document.querySelectorAll(".try-pane").forEach((pane) => {
    const on = pane.dataset.pane === beat;
    pane.classList.toggle("is-on", on);
    pane.hidden = !on;
  });
  syncRail();
  if (beat === "checker") {
    window.clearTimeout(healthTimer);
    healthTimer = window.setTimeout(() => kernel.restoreHealth(), 1400);
  }
  if (beat === "zip") zip.play();
}

const pressure = document.getElementById("try-pressure");
const flow = document.getElementById("try-flow");
let t = 0;
window.setInterval(() => {
  t += 1;
  if (pressure) pressure.textContent = `${(1.14 + Math.sin(t / 7) * 0.05).toFixed(2)} bar`;
  if (flow) flow.textContent = `${(0.2 + Math.sin(t / 11) * 0.03).toFixed(2)} L/min`;
}, 280);

document.querySelectorAll("[data-next]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const next = btn.dataset.next;
    unlocked.add(next);
    show(next);
  });
});

document.querySelector("[data-ask]").addEventListener("click", () => {
  const reply = document.querySelector("[data-reply]");
  reply.hidden = false;
  reply.classList.add("in");
  document.querySelector('[data-next="checker"]').disabled = false;
  unlocked.add("checker");
  syncRail();
});

document.querySelectorAll(".try-rail button").forEach((btn) => {
  btn.addEventListener("click", () => show(btn.dataset.beat));
});

syncRail();
show("watch");
