import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
const og =
  "https://raw.githubusercontent.com/shadybrook/certarig-platform/cursor/certarig-marketing-site-a496/site/public/og.svg";

function flattenJs(src) {
  const file = join(dist, src.replace(/^\//, ""));
  let js = readFileSync(file, "utf8");
  js = js.replace(/import\s*["'](\.\/[^"']+)["']\s*;?/g, (_, rel) => {
    const chunk = join(dirname(file), rel);
    return `${readFileSync(chunk, "utf8")};\n`;
  });
  if (/\bimport\b/.test(js)) {
    throw new Error(`${src} still has imports after flatten`);
  }
  return js;
}

function inlineHtml(name, rewrites = {}) {
  let html = readFileSync(join(dist, name), "utf8");
  html = html.replace(/<link rel="modulepreload"[^>]*>\s*/g, "");
  html = html.replace(/<link rel="stylesheet" crossorigin href="([^"]+)">/g, (_, href) => {
    const css = readFileSync(join(dist, href.replace(/^\//, "")), "utf8");
    return `<style>${css}</style>`;
  });
  html = html.replace(
    /<script type="module" crossorigin src="([^"]+)"><\/script>/g,
    (_, src) => `<script type="module">${flattenJs(src)}</script>`,
  );
  const fav = readFileSync(join(dist, "favicon.svg"), "utf8");
  const favUri = `data:image/svg+xml,${encodeURIComponent(fav)}`;
  html = html.replace(/href="\/favicon\.svg"/, `href="${favUri}"`);
  html = html.replace(/content="\/og\.svg"/, `content="${og}"`);
  for (const [from, to] of Object.entries(rewrites)) {
    html = html.replaceAll(from, to);
  }
  return html;
}

writeFileSync(
  join(root, "share.html"),
  inlineHtml("index.html", { 'href="/try"': 'href="./try-share.html"' }),
);
writeFileSync(
  join(root, "try-share.html"),
  inlineHtml("try.html", {
    'class="wordmark" href="/"': 'class="wordmark" href="./share.html"',
    'class="nav-quiet" href="/"': 'class="nav-quiet" href="./share.html"',
  }),
);
console.log("wrote site/share.html and site/try-share.html");
