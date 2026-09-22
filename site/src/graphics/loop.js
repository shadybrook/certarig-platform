import { tickCopy } from "../scroll.js";
import { checkerMarkup, stationMarkup } from "./bench.js";

const STEPS = ["watch", "match", "allow", "run", "leave"];

const COPY = {
  watch: "Watch.",
  match: "Match.",
  allow: "Allow.",
  run: "Run.",
  leave: "Leave.",
};

const FACES = {
  watch: {
    shell: "station",
    html: stationMarkup(),
  },
  match: {
    shell: "station",
    html: `
      <div class="station-card">
        <p class="station-kicker">This machine</p>
        <div class="match-cards">
          <div><span>The procedure</span><strong>match</strong></div>
          <div><span>This machine</span><strong>match</strong></div>
          <div><span>You applied the map</span><strong>ok</strong></div>
        </div>
      </div>
    `,
  },
  allow: {
    shell: "station",
    html: `
      <div class="station-card">
        <div class="fence">
          <div class="col">
            <strong>Agent may</strong>
            <ul>
              <li>pick a procedure</li>
              <li>write notes</li>
            </ul>
          </div>
          <div class="gap" aria-hidden="true"></div>
          <div class="col">
            <strong>Agent may not</strong>
            <ul>
              <li>bypass a lock</li>
              <li>raise a limit</li>
              <li>reset a trip</li>
            </ul>
          </div>
        </div>
      </div>
    `,
  },
  run: {
    shell: "checker",
    html: checkerMarkup({
      on: true,
      permit: true,
      estop: true,
      healthy: true,
      latched: false,
    }),
  },
  leave: {
    shell: "station",
    html: `
      <div class="station-card">
        <div class="restore-grid">
          <div><strong>Left</strong>As found</div>
          <div><strong>Took</strong>The zip</div>
        </div>
      </div>
    `,
  },
};

export function renderLoop(el) {
  el.innerHTML = `
    <div class="faces">
      ${STEPS.map((step) => {
        const spec = FACES[step];
        return `<div class="face" data-step="${step}">${spec.html}</div>`;
      }).join("")}
    </div>
  `;

  const title = document.getElementById("loop-title");
  const buttons = document.querySelectorAll(".loop-rail button");
  const bar = document.querySelector(".loop-scrub i");
  const faces = [...el.querySelectorAll(".face")];
  let current = "";
  let holdUntil = 0;

  function setStep(step, fromClick = false) {
    if (!STEPS.includes(step)) return;
    if (fromClick) holdUntil = Date.now() + 1600;
    else if (Date.now() < holdUntil) return;
    const idx = STEPS.indexOf(step);
    if (fromClick && bar) bar.style.transform = `scaleX(${idx / (STEPS.length - 1)})`;
    if (step !== current) {
      current = step;
      el.dataset.step = step;
      faces.forEach((n) => n.classList.toggle("is-on", n.dataset.step === step));
      buttons.forEach((btn) => {
        btn.setAttribute("aria-current", btn.dataset.step === step ? "true" : "false");
      });
      tickCopy(title, COPY[step]);
    }
  }

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => setStep(btn.dataset.step, true));
  });

  setStep("watch");

  return {
    setStep,
    stepFromProgress(p) {
      if (Date.now() < holdUntil) return;
      const i = Math.min(STEPS.length - 1, Math.round(p * (STEPS.length - 1)));
      setStep(STEPS[i]);
      if (bar) bar.style.transform = `scaleX(${p})`;
    },
    holding: () => Date.now() < holdUntil,
  };
}
