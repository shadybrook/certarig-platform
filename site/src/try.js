function outputOf(s) {
  return s.outputAllowed && s.permit && !s.tripLatched && s.estopClosed && s.healthy;
}

function storyOf(s) {
  if (s.story) return s.story;
  if (s.tripLatched && !s.healthy) return "trip";
  if (s.tripLatched) return "healthy";
  if (!outputOf(s) && !s.permit) return "reset";
  if (outputOf(s)) return "permit";
  return "run";
}

function glossOf(s) {
  if (s.tripLatched && (!s.healthy || !s.estopClosed)) return "The model does not get a vote.";
  if (s.tripLatched && s.healthy && s.estopClosed) return "Health does not restart it.";
  if (!s.tripLatched && !s.permit && s.healthy && s.estopClosed && s.outputAllowed) {
    return "Reset, then permit.";
  }
  return "";
}

function paintChecker(root, s) {
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
    story: "trip",
  };

  function apply(extra = {}) {
    Object.assign(state, extra);
    const on = paintChecker(el, state);
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
    state.story = "";
  }

  el.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    if (!btn || btn.disabled) return;
    const act = btn.dataset.act;
    if (act === "healthy") {
      if (state.healthy) {
        state.healthy = false;
        trip("Latched.");
      } else {
        state.healthy = true;
        state.note = "Still latched.";
        state.story = "healthy";
      }
    } else if (act === "estop") {
      if (state.estopClosed) {
        state.estopClosed = false;
        trip("E-stop open.");
      } else {
        state.estopClosed = true;
        state.note = "Still latched.";
        state.story = "";
      }
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
    restoreHealth() {
      if (!state.healthy) {
        state.healthy = true;
        state.note = "Still latched.";
        state.story = "healthy";
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
                ${s.notes ? `<span class="hash" data-named></span>` : ""}
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
const nameField = document.getElementById("try-name");
const proof = document.querySelector("[data-proof]");
const named = document.querySelector("[data-named]");

function setName(raw) {
  const clean = String(raw || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 48);
  if (proof) {
    proof.textContent = clean
      ? `${clean}. Proof from this classroom bench.`
      : "Proof you can take with you. This station stays here.";
  }
  if (named) named.textContent = clean;
}

nameField?.addEventListener("input", () => setName(nameField.value));

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
  document.body.dataset.beat = beat;
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
const pNeedle = document.querySelector('[data-needle="pressure"]');
const fNeedle = document.querySelector('[data-needle="flow"]');
let t = 0;
window.setInterval(() => {
  t += 1;
  const p = 1.14 + Math.sin(t / 7) * 0.05;
  const f = 0.2 + Math.sin(t / 11) * 0.03;
  if (pressure) pressure.textContent = p.toFixed(2);
  if (flow) flow.textContent = f.toFixed(2);
  if (pNeedle) pNeedle.setAttribute("transform", `rotate(${-20 + (p - 0.9) * 180} 70 78)`);
  if (fNeedle) fNeedle.setAttribute("transform", `rotate(${-50 + f * 80} 70 78)`);
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
