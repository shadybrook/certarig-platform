export function progressOf(track) {
  const r = track.getBoundingClientRect();
  const total = track.offsetHeight - window.innerHeight;
  if (total <= 1) return r.top < window.innerHeight * 0.4 ? 1 : 0;
  return Math.min(1, Math.max(0, -r.top / total));
}

export function onFrame(fn) {
  let ticking = false;
  const run = () => {
    ticking = false;
    fn();
  };
  const request = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(run);
    }
  };
  window.addEventListener("scroll", request, { passive: true });
  window.addEventListener("resize", request);
  fn();
  return () => {
    window.removeEventListener("scroll", request);
    window.removeEventListener("resize", request);
  };
}

export function tickCopy(node, text) {
  if (!node || node.textContent === text) return;
  node.textContent = text;
  node.classList.remove("tick");
  void node.offsetWidth;
  node.classList.add("tick");
}

export const reduced = () =>
  typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
