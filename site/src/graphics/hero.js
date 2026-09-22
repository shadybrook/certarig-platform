import { checkerMarkup, paintChecker } from "./bench.js";

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
        ${checkerMarkup({ on: false, permit: false, estop: true, healthy: false, latched: true })}
      </div>
    </div>
  `;

  const stage = el.querySelector(".gap-stage");
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
      paintChecker(el, {
        outputAllowed: true,
        permit: p > 0.78,
        tripLatched: p < 0.62,
        estopClosed: true,
        healthy: p > 0.38,
        note: "",
        story: p < 0.38 ? "trip" : p < 0.62 ? "healthy" : p < 0.78 ? "reset" : "permit",
      });
    },
  };
}
