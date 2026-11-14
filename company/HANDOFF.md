# Daily handoff

The weekday agents share one pull request. Each run starts on a fresh machine, so the handoff is git, not chat.

## Date

"Today" is the calendar date in Asia/Kolkata (IST, UTC+5:30). Use that date in every filename and title, including when the runner's clock is UTC.

## Branch and pull request

Base branch: `product/agent-lifecycle-2026-11-13`.

Daily head branch: `company/daily-YYYY-MM-DD`.

Pull request title: `CertaRig daily YYYY-MM-DD`.

The Listener creates the branch and opens the pull request. Later agents on the same date push onto that head branch. They do not open a second pull request for the same morning.

If the daily pull request is already merged, stop and write the reason in the run summary. Do not reopen yesterday's files.

## Files

All of today's files live in `company/runs/YYYY-MM-DD/`.

| Agent | File |
| --- | --- |
| Listener | `listener.md` |
| GTM | `gtm.md` |
| Marketing desk | `content-pack.md` |
| Source finder, Monday and Thursday | `sources.md` |
| Claim keeper, Friday | `claims.md` |

Copy the matching file in `company/templates/` and fill it. Leave a section blank when the source is missing. Write "Not found" and the path you checked. Do not invent a paragraph to fill the gap.

## Order

1. Listener reads [COMPANY.md](COMPANY.md), [channels.md](channels.md), and public pages. It commits `listener.md` and opens the pull request.
2. GTM reads `listener.md` from the open pull request. If that file is absent, it still writes `gtm.md`, marks the listener as missing, and chooses a bet that uses only [COMPANY.md](COMPANY.md).
3. Marketing desk reads `listener.md` and `gtm.md`. It writes `content-pack.md` on the same branch.
4. Source finder, on Monday and Thursday, adds `sources.md` to the same open pull request when it exists. If the morning pull request is missing, it opens `CertaRig sources YYYY-MM-DD` on `company/sources-YYYY-MM-DD` instead of inventing a daily branch.
5. Claim keeper, on Friday, reads the week's `company/runs/` files and the product docs named in its prompt. It adds `claims.md` to Friday's daily pull request.

## Commit

One commit per agent. Message shape:

```text
Add the CertaRig listener brief for YYYY-MM-DD
```

Use the role name: listener, GTM, content pack, source list, or claim review.

Do not commit under `evidence/`, `artifacts/`, or `docs/`. Do not change product code. Do not include secrets, operator keys, or account files. The demo key already printed in the README stays out of posts. Point readers at the README instead.

## Pull request note

The last agent to run on a day updates the pull request body to a list of the files added and one sentence on what the owner should do: publish, send, or discard. The owner merges or closes the pull request. Agents do not merge it.
