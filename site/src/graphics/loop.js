const STEPS = ["observe", "twin", "arm", "actuate", "restore"];

const FACES = {
  observe: {
    led: "bad",
    title: "observe · actuation 0",
    html: `
      <p class="face-label">Gate 2 · data quality before authority</p>
      <div class="traces">
        <div class="trace-card">
          <span>P1 · pressure</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path d="M0 48 C 20 48, 28 12, 50 12 S 80 52, 110 40 S 160 8, 200 18" fill="none" stroke="#0071e3" stroke-width="2"/>
            <line x1="0" y1="22" x2="200" y2="22" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>invalid once</strong>
          <span>envelope 10 bar · trip later 4.2</span>
        </div>
        <div class="trace-card">
          <span>P2 · flow</span>
          <svg viewBox="0 0 200 64" aria-hidden="true">
            <path d="M0 50 C 30 50, 40 20, 70 22 S 120 54, 150 36 S 180 16, 200 20" fill="none" stroke="#64d2ff" stroke-width="2"/>
            <line x1="0" y1="18" x2="200" y2="18" stroke="#c41e3a" stroke-dasharray="3 4" stroke-width="1"/>
          </svg>
          <strong>sweep required</strong>
          <span>envelope 20 L/min · trip later 15.0</span>
        </div>
      </div>
      <p class="lock"><b>Output authority locked.</b> First ADC run failed and was kept. Second pass: 1,291 samples, 129 s. Crossing a future trip while observing is not a permit.</p>
    `,
  },
  twin: {
    led: "gold",
    title: "twin · same procedure hash",
    html: `
      <p class="face-label">Gate 3 · do not improvise on metal</p>
      <div class="hash-row"><span>sim</span><span>adc_validation · relay · pressure · flow · dual · estop</span><em>pass</em></div>
      <div class="hash-row"><span>hw</span><span>same six hashes · 24 h stamp</span><em>match</em></div>
      <div class="hash-row"><span>map</span><span>rig.json applied by a human · never auto-energize</span><em>fence</em></div>
      <p class="stamp">twin-gate · procedure hash is the ticket, not a vibe</p>
    `,
  },
  arm: {
    led: "gold",
    title: "arm · capability fence",
    html: `
      <p class="face-label">Manifest is policy. Policy is never.</p>
      <div class="fence">
        <div class="col">
          <strong>Agent may</strong>
          <ul>
            <li>choose an approved procedure</li>
            <li>force_safe on its own</li>
            <li>write a transcript labelled narrative</li>
          </ul>
        </div>
        <div class="gap" aria-hidden="true"></div>
        <div class="col">
          <strong>Agent may not</strong>
          <ul>
            <li>bypass_interlock — not a tool</li>
            <li>override_limits — not a tool</li>
            <li>ack_operator_step, reset_trip, shutdown</li>
          </ul>
        </div>
      </div>
      <p class="never">428 from the agent deep-links to Approvals. A person owns the irreversible act.</p>
    `,
  },
  actuate: {
    led: "ok",
    title: "actuate · kernel owns GPIO",
    html: `
      <p class="face-label">Gate 4 · Fake selected procedures. Fake did not compare numbers.</p>
      <div class="and-bus">
        <div class="and-term" data-ok="true"><span>actuation enabled</span><i></i></div>
        <div class="and-term" data-ok="true"><span>permit requested</span><i></i></div>
        <div class="and-term" data-ok="true"><span>trip not latched</span><i></i></div>
        <div class="and-term" data-ok="true"><span>e-stop closed</span><i></i></div>
        <div class="and-term" data-ok="true"><span>process healthy</span><i></i></div>
      </div>
      <div class="out-lamp" data-on="true"><span class="bulb"></span> Commanded output high — not contact motion, not load current.</div>
    `,
  },
  restore: {
    led: "ok",
    title: "restore · proof includes leaving",
    html: `
      <p class="face-label">Gate 5 · success is the previous system, intact</p>
      <div class="restore-grid">
        <div>
          <strong>Returned</strong>
          Phase 3 dashboard on :8080, observe-only. Sidecar stopped. Actuation held at 0. Pi halted.
        </div>
        <div>
          <strong>Written</strong>
          Checksummed bundle. Ledger row. Restoration is in the evidence, not a slide.
        </div>
      </div>
      <p class="stamp">if you cannot leave the bench, the run is not finished</p>
    `,
  },
};

function face(step) {
  const spec = FACES[step];
  return `
    <div class="instrument" data-step="${step}">
      <div class="instrument-chrome">
        <span class="led" data-tone="${spec.led}"></span>
        <span>CertaRig · mapped rig</span>
        <span class="spacer">${spec.title}</span>
      </div>
      <div class="instrument-face">${spec.html}</div>
    </div>
  `;
}

export function renderLoop(el) {
  const setStep = (step) => {
    el.dataset.step = step;
    el.innerHTML = face(step);
    document.querySelectorAll(".loop-rail button").forEach((btn) => {
      btn.setAttribute("aria-current", btn.dataset.step === step ? "true" : "false");
    });
  };

  setStep("observe");

  document.querySelectorAll(".loop-rail button").forEach((btn) => {
    btn.addEventListener("click", () => {
      setStep(btn.dataset.step);
      document.getElementById(`step-${btn.dataset.step}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });

  const chapters = document.querySelectorAll(".loop-chapters article");
  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setStep(visible.target.dataset.step);
    },
    { rootMargin: "-30% 0px -40% 0px", threshold: [0.25, 0.5, 0.75] },
  );
  chapters.forEach((n) => io.observe(n));
  return STEPS;
}
