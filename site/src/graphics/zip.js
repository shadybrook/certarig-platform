const ARCHIVE =
  "b73426a1eb01eeb29a58c34d3fbbdbc51321660b7a804361650f440afd8346df";
const MANIFEST =
  "a2338aa9c3b0ae78ee29426fbfbd79bbb68e91750f815624dc140d912f98ada5";

const SHEETS = [
  { name: "SHA256SUMS", hash: "", offset: 0, narrative: false },
  { name: "manifest.json", hash: "", offset: 10, narrative: false },
  { name: "report.md", hash: "", offset: 20, narrative: false },
  { name: "events.jsonl", hash: "", offset: 30, narrative: false },
  { name: "narrative.md", hash: "narrative", offset: 48, narrative: true },
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
      <div class="zip-sheet${s.narrative ? " narrative" : ""}" style="--offset:${s.offset}px">
        <span>${s.name}</span>
        <span class="hash">${s.hash}</span>
      </div>
    `,
  ).join("");

  el.innerHTML = `
    <div class="instrument">
      <div class="instrument-chrome">
        <span class="led" data-tone="gold"></span>
        <span>zip</span>
        <span class="spacer">rehash</span>
      </div>
      <div class="instrument-face zip-face">
        <div class="zip-stack">${sheets}</div>
        <div class="zip-actions">
          <button type="button" data-rehash>Rehash</button>
          <span class="rehash-out" aria-live="polite">CSV missing. Defect.</span>
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
      step += 3;
      out.textContent = `sha256(archive)  ${hexWalk(ARCHIVE, step)}`;
      if (step >= 64) {
        window.clearInterval(timer);
        out.innerHTML = `sha256(archive)&nbsp;&nbsp;${ARCHIVE}<br>sha256(manifest)&nbsp;${MANIFEST}`;
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
