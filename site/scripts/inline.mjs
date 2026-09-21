import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
let html = readFileSync(join(dist, "index.html"), "utf8");

html = html.replace(
  /<link rel="stylesheet" crossorigin href="([^"]+)">/,
  (_, href) => {
    const css = readFileSync(join(dist, href.replace(/^\//, "")), "utf8");
    return `<style>${css}</style>`;
  },
);
html = html.replace(
  /<script type="module" crossorigin src="([^"]+)"><\/script>/,
  (_, src) => {
    const js = readFileSync(join(dist, src.replace(/^\//, "")), "utf8");
    return `<script type="module">${js}</script>`;
  },
);

const fav = readFileSync(join(dist, "favicon.svg"), "utf8");
const favUri = `data:image/svg+xml,${encodeURIComponent(fav)}`;
html = html.replace(/href="\/favicon\.svg"/, `href="${favUri}"`);
html = html.replace(/content="\/og\.svg"/, `content="https://raw.githubusercontent.com/shadybrook/certarig-platform/cursor/certarig-marketing-site-a496/site/public/og.svg"`);

writeFileSync(join(root, "share.html"), html);
console.log("wrote site/share.html", html.length, "bytes");
