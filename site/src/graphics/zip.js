const DEMO =
  "c1e0a94b7d2f18e6a0c35b91d47e82f0b6a19c4d8e27f53a10b8c6d4e9f20173";

const SHEETS = [
  { name: "checksums", offset: 0, notes: false },
  { name: "manifest", offset: 10, notes: false },
  { name: "report", offset: 20, notes: false },
  { name: "log", offset: 30, notes: false },
  { name: "notes", offset: 48, notes: true },
];

function hexWalk(target, step) {
  const chars = "0123456789abcdef";
  return target
    .split("")
    .map((ch, i) => (i < step ? ch : chars[(i * 7 + step) % 16]))
    .join("");
}

export function renderZip(el) {
  const sheets = SHEETS.map(
    (s) => `
      <div class="zip-sheet${s.notes ? " narrative" : ""}" style="--offset:${s.offset}px">
        <span>${s.name}</span>
      </div>
    `,
  ).join("");

  el.innerHTML = `
    <div class="instrument">
      <div class="instrument-chrome">
        <span class="led" data-tone="gold"></span>
        <span>evidence zip</span>
        <span class="spacer">rehash</span>
      </div>
      <div class="instrument-face zip-face">
        <div class="zip-stack">${sheets}</div>
        <div class="zip-actions">
          <button type="button" data-rehash>Rehash</button>
          <span class="rehash-out" aria-live="polite"></span>
        </div>
      </div>
    </div>
  `;

  const nodes = [...el.querySelectorAll(".zip-sheet")];
  const out = el.querySelector(".rehash-out");
  const btn = el.querySelector("[data-rehash]");
  let timer = 0;
  let done = false;

  function rehash() {
    window.clearInterval(timer);
    let step = 0;
    btn.disabled = true;
    timer = window.setInterval(() => {
      step += 4;
      out.textContent = hexWalk(DEMO, step);
      if (step >= 64) {
        window.clearInterval(timer);
        out.textContent = "Match.";
        btn.disabled = false;
        done = true;
      }
    }, 24);
  }

  btn.addEventListener("click", () => {
    done = false;
    rehash();
  });

  return {
    setProgress(p) {
      nodes.forEach((node, i) => {
        const edge = (i + 0.15) / (nodes.length + 0.4);
        const on = p > edge;
        node.classList.toggle("in", on);
        const local = Math.min(1, Math.max(0, (p - edge) / 0.12));
        node.style.transform = on ? `translateY(${(1 - local) * 16}px)` : "translateY(18px)";
      });
      if (p > 0.72 && !done && !btn.disabled) rehash();
    },
    rehash,
  };
}
