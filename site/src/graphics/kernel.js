function outputOf(s) {
  return s.actuationEnabled && s.permit && !s.tripLatched && s.estopClosed && s.healthy;
}

function termRow(ok, label) {
  return `<div class="and-term" data-ok="${ok}"><span>${label}</span><i></i></div>`;
}

export function renderKernel(el) {
  const state = {
    actuationEnabled: true,
    permit: true,
    tripLatched: false,
    estopClosed: true,
    healthy: true,
    note: "All five terms true. Output may energize. This is commanded GPIO, not a SIL loop.",
  };

  function trip(why) {
    state.tripLatched = true;
    state.permit = false;
    state.note = why;
  }

  function paint() {
    const on = outputOf(state);
    const resetOk = state.tripLatched && state.healthy && state.estopClosed;
    const permitOk = !state.tripLatched && state.healthy && state.estopClosed && state.actuationEnabled && !state.permit;
    el.innerHTML = `
      <div class="instrument">
        <div class="instrument-chrome">
          <span class="led" data-tone="${on ? "ok" : "bad"}"></span>
          <span>kernel · drive_high</span>
          <span class="spacer">${on ? "OUTPUT 1" : "OUTPUT 0"}</span>
        </div>
        <div class="instrument-face">
          <p class="face-label">Try the conjunction. Language is not in this panel.</p>
          <div class="and-bus">
            ${termRow(state.actuationEnabled, "actuation enabled")}
            ${termRow(state.permit, "permit requested")}
            ${termRow(!state.tripLatched, "trip not latched")}
            ${termRow(state.estopClosed, "emergency stop closed")}
            ${termRow(state.healthy, "process healthy")}
          </div>
          <div class="out-lamp" data-on="${on}">
            <span class="bulb"></span>
            ${on ? "Output true — kernel said yes." : "Output false — kernel said no."}
          </div>
          <div class="kernel-controls">
            <button class="term-toggle" type="button" data-act="actuation" aria-pressed="${state.actuationEnabled}">
              Actuation policy: ${state.actuationEnabled ? "enabled" : "held at 0"}
            </button>
            <button class="term-toggle" type="button" data-act="healthy" aria-pressed="${state.healthy}">
              Process: ${state.healthy ? "healthy" : "over-limit"}
            </button>
            <button class="term-toggle" type="button" data-act="estop" aria-pressed="${state.estopClosed}">
              E-stop: ${state.estopClosed ? "closed" : "open"}
            </button>
            <button type="button" data-act="reset" ${resetOk ? "" : "disabled"}>Reset trip</button>
            <button class="primary" type="button" data-act="permit" ${permitOk ? "" : "disabled"}>Request permit</button>
          </div>
          <p class="status-line" aria-live="polite">${state.note}</p>
        </div>
      </div>
    `;
    el.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const act = btn.dataset.act;
        if (act === "actuation") {
          state.actuationEnabled = !state.actuationEnabled;
          if (!state.actuationEnabled) {
            state.permit = false;
            state.note = "Actuation held at 0. Permit cleared. CERTARIG_ENABLE_ACTUATION stays 0 until a human inspects the bench.";
          } else {
            state.note = "Actuation enabled. Output stays false until a new permit. Enabling is not a yes.";
          }
        } else if (act === "healthy") {
          if (state.healthy) {
            state.healthy = false;
            trip("Process over-limit. Trip latched, permit cleared. Returning to healthy does not restart the output.");
          } else {
            state.healthy = true;
            state.note = "Process healthy again. Trip still latched. No auto-restart.";
          }
        } else if (act === "estop") {
          if (state.estopClosed) {
            state.estopClosed = false;
            trip("E-stop open. Forced safe. Releasing the loop will not restore a previous permit.");
          } else {
            state.estopClosed = true;
            state.note = "E-stop closed. Still latched. Still no permit. That is the point.";
          }
        } else if (act === "reset") {
          state.tripLatched = false;
          state.permit = false;
          state.note = "Reset accepted after healthy observation. Now a human may request a new permit.";
        } else if (act === "permit") {
          state.permit = true;
          state.note = "Permit requested. If every other term holds, the kernel — not the agent — said yes.";
        }
        paint();
      });
    });
  }

  paint();
}
