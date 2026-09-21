import { tickCopy } from "../scroll.js";

const STEPS = ["observe", "twin", "arm", "actuate", "restore"];

const COPY = {
  observe: ["Observe.", "Data quality before authority."],
  twin: ["Twin.", "Same hash. Then metal."],
  arm: ["Arm.", "Bypass is not a tool."],
  actuate: ["Actuate.", "Only the kernel says yes."],
  restore: ["Restore.", "Leaving is part of the proof."],
};

const FACES = {
  observe: {
    led: "bad",
    title: "observe · actuation 0",
    html: `
      <p class="face-label">Before output authority</p>
      <div class="traces">
        <div class="trace-card">
          <span>P1 · pressure</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path class="wave" d="M0 48 C 20 48, 28 12, 50 12 S 80 52, 110 40 S 160 8, 200 18" fill="none" stroke="#0071e3" stroke-width="2"/>
            <line x1="0" y1="22" x2="200" y2="22" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>invalid once</strong>
          <span>kept the failure</span>
        </div>
        <div class="trace-card">
          <span>P2 · flow</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path class="wave" d="M0 50 C 30 50, 40 20, 70 22 S 120 54, 150 36 S 180 16, 200 20" fill="none" stroke="#64d2ff" stroke-width="2"/>
            <line x1="0" y1="18" x2="200" y2="18" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>sweep required</strong>
          <span>not a permit</span>
        </div>
      </div>
      <p class="lock">Output locked.</p>
    `,
  },
  twin: {
    led: "gold",
    title: "twin · same procedure hash",
    html: `
      <p class="face-label">Do not improvise on metal</p>
      <div class="hash-row"><span>sim</span><span>six procedures</span><em>pass</em></div>
      <div class="hash-row"><span>hw</span><span>same hashes · 24 h</span><em>match</em></div>
      <div class="hash-row"><span>map</span><span>human applies rig.json</span><em>fence</em></div>
      <p class="stamp">a guessed map never auto-energizes</p>
    `,
  },
  arm: {
    led: "gold",
    title: "arm · capability fence",
    html: `
      <p class="face-label">Policy is never</p>
      <div class="fence">
        <div class="col">
          <strong>Agent may</strong>
          <ul>
            <li>choose an approved procedure</li>
            <li>write narrative</li>
          </ul>
        </div>
        <div class="gap" aria-hidden="true"></div>
        <div class="col">
          <strong>Agent may not</strong>
          <ul>
            <li>bypass_interlock</li>
            <li>override_limits</li>
            <li>reset_trip · shutdown</li>
          </ul>
        </div>
      </div>
      <p class="never">428 → a human on Approvals.</p>
    `,
  },
  actuate: {
    led: "ok",
    title: "actuate · kernel owns GPIO",
    html: `
      <p class="face-label">Fake selected. Fake did not compare.</p>
      <div class="and-bus">
        <div class="and-term" data-ok="true"><span>actuation enabled</span><i></i></div>
        <div class="and-term" data-ok="true"><span>permit requested</span><i></i></div>
        <div class="and-term" data-ok="true"><span>trip not latched</span><i></i></div>
        <div class="and-term" data-ok="true"><span>e-stop closed</span><i></i></div>
        <div class="and-term" data-ok="true"><span>process healthy</span><i></i></div>
      </div>
      <div class="out-lamp" data-on="true"><span class="bulb"></span> Commanded output — not contact motion.</div>
    `,
  },
  restore: {
    led: "ok",
    title: "restore · proof includes leaving",
    html: `
      <p class="face-label">Success is the previous system, intact</p>
      <div class="restore-grid">
        <div><strong>Returned</strong>Observe-only. Actuation 0. Halted.</div>
        <div><strong>Written</strong>Checksummed bundle. Ledger row.</div>
      </div>
      <p class="stamp">if you cannot leave the bench, the run is not finished</p>
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
                <span>CertaRig · mapped rig</span>
                <span class="spacer">${spec.title}</span>
              </div>
              <div class="instrument-face">${spec.html}</div>
            </div>
          </div>`;
      }).join("")}
    </div>
  `;

  const title = document.getElementById("loop-title");
  const line = document.getElementById("loop-line");
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
      tickCopy(title, COPY[step][0]);
      if (line) line.textContent = COPY[step][1];
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
