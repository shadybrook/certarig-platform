import { tickCopy } from "../scroll.js";

const STEPS = ["observe", "twin", "arm", "actuate", "restore"];

const COPY = {
  observe: "Observe.",
  twin: "Twin.",
  arm: "Arm.",
  actuate: "Actuate.",
  restore: "Restore.",
};

const FACES = {
  observe: {
    led: "bad",
    title: "observe",
    html: `
      <div class="traces">
        <div class="trace-card">
          <span>P1</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path class="wave" d="M0 48 C 20 48, 28 12, 50 12 S 80 52, 110 40 S 160 8, 200 18" fill="none" stroke="#0071e3" stroke-width="2"/>
            <line x1="0" y1="22" x2="200" y2="22" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>invalid</strong>
        </div>
        <div class="trace-card">
          <span>P2</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path class="wave" d="M0 50 C 30 50, 40 20, 70 22 S 120 54, 150 36 S 180 16, 200 20" fill="none" stroke="#64d2ff" stroke-width="2"/>
            <line x1="0" y1="18" x2="200" y2="18" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>locked</strong>
        </div>
      </div>
    `,
  },
  twin: {
    led: "gold",
    title: "twin",
    html: `
      <div class="hash-row"><span>sim</span><span>six procedures</span><em>pass</em></div>
      <div class="hash-row"><span>hw</span><span>same hashes</span><em>match</em></div>
      <div class="hash-row"><span>map</span><span>rig.json</span><em>fence</em></div>
    `,
  },
  arm: {
    led: "gold",
    title: "arm",
    html: `
      <div class="fence">
        <div class="col">
          <strong>May</strong>
          <ul>
            <li>approved procedure</li>
            <li>narrative</li>
          </ul>
        </div>
        <div class="gap" aria-hidden="true"></div>
        <div class="col">
          <strong>May not</strong>
          <ul>
            <li>bypass_interlock</li>
            <li>override_limits</li>
            <li>reset_trip</li>
          </ul>
        </div>
      </div>
    `,
  },
  actuate: {
    led: "ok",
    title: "actuate",
    html: `
      <div class="and-bus">
        <div class="and-term" data-ok="true"><span>actuation enabled</span><i></i></div>
        <div class="and-term" data-ok="true"><span>permit requested</span><i></i></div>
        <div class="and-term" data-ok="true"><span>trip not latched</span><i></i></div>
        <div class="and-term" data-ok="true"><span>e-stop closed</span><i></i></div>
        <div class="and-term" data-ok="true"><span>process healthy</span><i></i></div>
      </div>
      <div class="out-lamp" data-on="true"><span class="bulb"></span></div>
    `,
  },
  restore: {
    led: "ok",
    title: "restore",
    html: `
      <div class="restore-grid">
        <div><strong>Returned</strong>Actuation 0</div>
        <div><strong>Written</strong>The zip</div>
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
                <span>CertaRig</span>
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

  setStep("observe");

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
