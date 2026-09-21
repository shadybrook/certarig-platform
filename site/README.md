# CertaRig marketing site

Public page for the ideology: language interprets, numbers decide, the kernel is the only yes, the zip is the proof. Paying customers: **zero**. Not a claim that an AI drives GPIO.

```bash
cd site
npm ci
npm run dev      # http://127.0.0.1:5173
npm run build    # site/dist plus inlined site/share.html
npm run preview  # http://127.0.0.1:4173
```

## Send to VCs

1. **Vercel (intended production).** Repo-root `vercel.json` builds this folder. In Vercel: Import `shadybrook/certarig-platform`, leave Root Directory as the repository root. The first production URL is whatever Vercel assigns (`*.vercel.app`). From a laptop with the CLI: `npx vercel --yes` in this repo after `npx vercel login`.
2. **Inlined single file** committed as `site/share.html` for a host that can serve a raw HTML file (see the share kit note). Rebuild refreshes it.

Netlify is wired the same way (`netlify.toml` → `site/dist`) if that host is used instead.
