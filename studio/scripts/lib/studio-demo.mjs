/** Shared login and caption helpers for Studio demo films. */

export const OPERATOR = "sim-operator-key-000001";

const CAPTION_CSS = `
#cr-caption, #cr-card {
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
}
#cr-caption {
  position: fixed; left: 28px; right: 28px; bottom: 24px; z-index: 9999;
  padding: 14px 18px; border-radius: 12px;
  background: rgba(14, 17, 22, 0.9); color: #e8edf5;
  font-size: 22px; letter-spacing: 0.01em; pointer-events: none;
  border: 1px solid #2a3140;
}
#cr-card {
  position: fixed; inset: 0; z-index: 10000;
  display: none; place-items: center; text-align: center;
  background: #0e1116; color: #e8edf5;
}
#cr-card.on { display: grid; }
#cr-card .kicker {
  color: #93a0b5; letter-spacing: 0.16em; text-transform: uppercase; font-size: 13px; margin: 0;
}
#cr-card h1 { font-size: 44px; font-weight: 600; margin: 16px 32px 0; max-width: 18ch; line-height: 1.15; }
#cr-card .end { color: #93a0b5; margin-top: 20px; font-size: 18px; }
`;

export async function launchBrowser(chromium) {
  try {
    return await chromium.launch({ channel: "chrome", headless: true });
  } catch {
    return await chromium.launch({ headless: true });
  }
}

export async function login(page, base) {
  await page.goto(`${base}/`);
  await page.getByTestId("operator-key").fill(OPERATOR);
  await page.getByRole("button", { name: "Open Studio" }).click();
  await page.locator("#health-pill").waitFor({ state: "visible", timeout: 15_000 });
}

export async function injectOverlays(page) {
  await page.addStyleTag({ content: CAPTION_CSS });
  await page.evaluate(() => {
    if (!document.getElementById("cr-caption")) {
      const caption = document.createElement("div");
      caption.id = "cr-caption";
      caption.style.display = "none";
      document.body.appendChild(caption);
    }
    if (!document.getElementById("cr-card")) {
      const card = document.createElement("div");
      card.id = "cr-card";
      card.innerHTML = '<p class="kicker"></p><h1></h1><p class="end"></p>';
      document.body.appendChild(card);
    }
  });
}

export async function showCaption(page, text) {
  await page.evaluate((value) => {
    const caption = document.getElementById("cr-caption");
    const card = document.getElementById("cr-card");
    card.classList.remove("on");
    caption.textContent = value;
    caption.style.display = value ? "block" : "none";
  }, text);
}

export async function showCard(page, { kicker = "", title, end = "" }) {
  await page.evaluate(({ kicker, title, end }) => {
    const card = document.getElementById("cr-card");
    card.querySelector(".kicker").textContent = kicker;
    card.querySelector("h1").textContent = title;
    card.querySelector(".end").textContent = end;
    card.classList.add("on");
    document.getElementById("cr-caption").style.display = "none";
  }, { kicker, title, end });
}

export async function hideCard(page) {
  await page.evaluate(() => document.getElementById("cr-card").classList.remove("on"));
}

export function clock() {
  const started = Date.now();
  return async (page, markMs) => {
    const wait = started + markMs - Date.now();
    if (wait > 0) await page.waitForTimeout(wait);
  };
}

export async function waitForEvidenceHash(page) {
  await page.locator('#nav a[data-view="evidence"]').click();
  await page.locator("#export-all").waitFor({ state: "visible", timeout: 15_000 });
  await page.locator("#export-all").click();
  await page.locator("#view-evidence code").first().waitFor({ state: "visible", timeout: 15_000 });
}
