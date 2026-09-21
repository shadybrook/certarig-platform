import { tickCopy } from "../scroll.js";

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
    led: "bad",
    title: "watch",
    html: `
      <div class="traces">
        <div class="trace-card">
          <span>Pressure</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path class="wave" d="M0 48 C 20 48, 28 12, 50 12 S 80 52, 110 40 S 160 8, 200 18" fill="none" stroke="#0071e3" stroke-width="2"/>
            <line x1="0" y1="22" x2="200" y2="22" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>high</strong>
        </div>
        <div class="trace-card">
          <span>Flow</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path class="wave" d="M0 50 C 30 50, 40 20, 70 22 S 120 54, 150 36 S 180 16, 200 20" fill="none" stroke="#64d2ff" stroke-width="2"/>
            <line x1="0" y1="18" x2="200" y2="18" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>held</strong>
        </div>
      </div>
    `,
  },
  match: {
    led: "gold",
    title: "match",
    html: `
      <div class="hash-row"><span>model</span><span>the procedure</span><em>match</em></div>
      <div class="hash-row"><span>rig</span><span>this machine</span><em>match</em></div>
      <div class="hash-row"><span>map</span><span>you applied it</span><em>ok</em></div>
    `,
  },
  allow: {
    led: "gold",
    title: "allow",
    html: `
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
    `,
  },
  run: {
    led: "ok",
    title: "run",
    html: `
      <div class="and-bus">
        <div class="and-term" data-ok="true"><span>output allowed</span><i></i></div>
        <div class="and-term" data-ok="true"><span>permit on</span><i></i></div>
        <div class="and-term" data-ok="true"><span>not tripped</span><i></i></div>
        <div class="and-term" data-ok="true"><span>e-stop closed</span><i></i></div>
        <div class="and-term" data-ok="true"><span>process healthy</span><i></i></div>
      </div>
      <div class="out-lamp" data-on="true"><span class="bulb"></span></div>
    `,
  },
  leave: {
    led: "ok",
    title: "leave",
    html: `
      <div class="restore-grid">
        <div><strong>Left</strong>As found</div>
        <div><strong>Took</strong>The zip</div>
      </div>
    `,
  },
};

export function renderLoop(el) {
  el.innerHTML = `
    <div class="faces">
      ${STEPS.map((step) => {
        const spec = FACES[step];
        return `
          <div class="face" data-step="${step}">
            <div class="instrument">
              <div class="instrument-chrome">
                <span class="led" data-tone="${spec.led}"></span>
                <span>mapped rig</span>
                <span class="spacer">${spec.title}</span>
              </div>
              <div class="instrument-face">${spec.html}</div>
            </div>
          </div>`;
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
