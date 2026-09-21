import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = dirname(fileURLToPath(import.meta.url));

const tryPath = {
  name: "try-path",
  configureServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url === "/try" || req.url === "/try/") req.url = "/try.html";
      next();
    });
  },
  configurePreviewServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url === "/try" || req.url === "/try/") req.url = "/try.html";
      next();
    });
  },
};

export default defineConfig({
  root: ".",
  base: "/",
  plugins: [tryPath],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsInlineLimit: 4096,
    rollupOptions: {
      input: {
        main: resolve(root, "index.html"),
        try: resolve(root, "try.html"),
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
  },
});
