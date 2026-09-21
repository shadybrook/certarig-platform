const TERMS = [
  "output allowed",
  "permit on",
  "not tripped",
  "e-stop closed",
  "process healthy",
];

export function renderHero(el) {
  el.innerHTML = `
    <div class="gap-stage" data-phase="0">
      <div class="gap-lang">
        <div class="bubble" data-b="0">“Run the pressure test.”</div>
        <div class="bubble" data-b="1">“Why did it stop?”</div>
        <p class="stops">stops here</p>
      </div>
      <div class="gap-bar" aria-hidden="true"></div>
      <div class="gap-kernel">
        <div class="and-bus">
          ${TERMS.map((t) => `<div class="and-term" data-ok="false"><span>${t}</span><i></i></div>`).join("")}
        </div>
        <div class="out-lamp" data-on="false">
          <span class="bulb"></span>
          <span class="lamp-copy">off</span>
        </div>
      </div>
    </div>
  `;

  const stage = el.querySelector(".gap-stage");
  const terms = [...el.querySelectorAll(".and-term")];
  const lamp = el.querySelector(".out-lamp");
  const copy = el.querySelector(".lamp-copy");
  const bubbles = [...el.querySelectorAll(".bubble")];
  let last = -1;

  return {
    play(p) {
      const phase = p < 0.12 ? 0 : p < 0.28 ? 1 : p < 0.42 ? 2 : p < 0.72 ? 3 : 4;
      if (phase !== last) {
        last = phase;
        stage.dataset.phase = String(phase);
      }
      bubbles.forEach((b, i) => {
        b.classList.toggle("in", p > 0.04 + i * 0.12);
      });
      stage.classList.toggle("stopped", p > 0.32);
      terms.forEach((t, i) => {
        t.setAttribute("data-ok", String(p > 0.42 + i * 0.07));
      });
      const out = p > 0.82;
      lamp.dataset.on = String(out);
      copy.textContent = out ? "on" : "off";
    },
  };
}
