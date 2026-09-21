# CertaRig marketing site

Public page for the ideology: language interprets, numbers decide, the kernel is the only yes, the zip is the proof. Paying customers: **zero**. Not a claim that an AI drives GPIO.

```bash
cd site
npm ci
npm run dev      # http://127.0.0.1:5173
npm run build
npm run preview  # http://127.0.0.1:4173
```

## Vercel

Repo root `vercel.json` builds this folder. In the Vercel project:

- Root Directory: repository root (uses `vercel.json`), **or**
- Root Directory: `site` (Vite auto-detect)

Production URL is whatever Vercel assigns after the GitHub project is linked (`npx vercel --yes` from `site/` also works with a logged-in CLI).
