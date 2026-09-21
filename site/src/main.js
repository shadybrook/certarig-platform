import { renderHero } from "./graphics/hero.js";
import { renderLoop } from "./graphics/loop.js";
import { renderKernel } from "./graphics/kernel.js";
import { renderZip } from "./graphics/zip.js";
import { onFrame, progressOf, reduced } from "./scroll.js";

const hero = renderHero(document.querySelector("#hero-graphic"));
const loop = renderLoop(document.querySelector("#loop-graphic"));
const kernel = renderKernel(document.querySelector("#kernel-graphic"));
const zip = renderZip(document.querySelector("#zip-graphic"));

const gapTrack = document.querySelector('[data-scene="gap"]');
const loopTrack = document.querySelector('[data-scene="loop"]');
const kernelTrack = document.querySelector('[data-scene="kernel"]');
const zipTrack = document.querySelector('[data-scene="zip"]');
const quiet = reduced();

const target = { gap: 0, loop: 0, kernel: 0, zip: 0 };
const scrub = { gap: 0, loop: 0, kernel: 0, zip: 0 };

function sample() {
  if (gapTrack) target.gap = progressOf(gapTrack);
  if (loopTrack) target.loop = progressOf(loopTrack);
  if (kernelTrack) target.kernel = progressOf(kernelTrack);
  if (zipTrack) target.zip = progressOf(zipTrack);
  if (kernelTrack) {
    const r = kernelTrack.getBoundingClientRect();
    document.body.classList.toggle("on-dark", r.top < 64 && r.bottom > window.innerHeight * 0.45);
  }
}

function paint(useTarget) {
  const g = useTarget ? target : scrub;
  hero.play(g.gap);
  loop.stepFromProgress(g.loop);
  kernel.play(g.kernel);
  zip.setProgress(g.zip);
}

if (!quiet) {
  onFrame(sample);
  const ease = 0.14;
  const tick = () => {
    let moving = false;
    for (const k of Object.keys(scrub)) {
      const next = scrub[k] + (target[k] - scrub[k]) * ease;
      if (Math.abs(next - scrub[k]) > 0.0004) moving = true;
      scrub[k] = Math.abs(next - target[k]) < 0.001 ? target[k] : next;
    }
    paint(false);
    requestAnimationFrame(tick);
    if (!moving) {
      /* keep the loop — Apple pages stay live so wheel ticks never hitch */
    }
  };
  sample();
  paint(true);
  requestAnimationFrame(tick);

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) e.target.classList.add("in");
      });
    },
    { threshold: 0.28 },
  );
  document.querySelectorAll(".statement, .proof, .honest").forEach((n) => {
    n.classList.add("reveal");
    io.observe(n);
  });
} else {
  sample();
  paint(true);
  zip.setProgress(1);
}
