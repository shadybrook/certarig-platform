const ARCHIVE =
  "b73426a1eb01eeb29a58c34d3fbbdbc51321660b7a804361650f440afd8346df";
const MANIFEST =
  "a2338aa9c3b0ae78ee29426fbfbd79bbb68e91750f815624dc140d912f98ada5";

const SHEETS = [
  { name: "SHA256SUMS", hash: "the contract a stranger re-runs", offset: 0, narrative: false },
  { name: "manifest.json", hash: "a2338aa9c3b0ae78…2f98ada5", offset: 10, narrative: false },
  { name: "report.md", hash: "numbers from the kernel", offset: 20, narrative: false },
  { name: "events.jsonl", hash: "procedure · checks · latch", offset: 30, narrative: false },
  { name: "narrative.md", hash: "labelled NARRATIVE · never the measurement", offset: 48, narrative: true },
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
        <span>evidence bundle</span>
        <span class="spacer">auditor · read-only</span>
      </div>
      <div class="instrument-face zip-face">
        <p class="face-label">12 Sep pulled zip · run_20260912T162352_6515a9</p>
        <div class="zip-stack">${sheets}</div>
        <div class="zip-actions">
          <button type="button" data-rehash>Rehash as a stranger</button>
          <span class="rehash-out" aria-live="polite">No CertaRig install required. Open the sums file. Hash one file by hand.</span>
        </div>
      </div>
    </div>
  `;

  const out = el.querySelector(".rehash-out");
  const btn = el.querySelector("[data-rehash]");
  let timer = 0;
  btn.addEventListener("click", () => {
    window.clearInterval(timer);
    let step = 0;
    btn.disabled = true;
    timer = window.setInterval(() => {
      step += 2;
      out.textContent = `sha256(archive)  ${hexWalk(ARCHIVE, step)}`;
      if (step >= 64) {
        window.clearInterval(timer);
        out.innerHTML = `sha256(archive)&nbsp;&nbsp;${ARCHIVE}<br>sha256(manifest)&nbsp;${MANIFEST}<br>CSV waveforms are not yet inside this export. That is a defect.`;
        btn.disabled = false;
      }
    }, 28);
  });
}
