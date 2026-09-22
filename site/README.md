# CertaRig marketing site

Public product page: the agent may ask, only the kernel may say yes, the zip is the proof. A separate checker owns the on-switch.

**Try it** is a static classroom bench at `/try` (pressure + flow). No operator keys, no simulator, no Pi.

```bash
cd site
npm ci
npm run dev      # http://127.0.0.1:5173
npm run build    # site/dist plus inlined site/share.html and site/try-share.html
npm run preview  # http://127.0.0.1:4173
```

## Send to VCs

1. **Vercel (intended production).** Repo-root `vercel.json` builds this folder. `/try` rewrites to `try.html`. In Vercel: Import `shadybrook/certarig-platform`, leave Root Directory as the repository root.
2. **Inlined files** committed as `site/share.html` (film) and `site/try-share.html` (bench). Rebuild refreshes them.

Netlify is wired the same way (`netlify.toml` → `site/dist`) if that host is used instead.
