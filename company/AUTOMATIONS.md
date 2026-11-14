# Turn the company on

Create these at [cursor.com/automations](https://cursor.com/automations) after `company/` is on `product/agent-lifecycle-2026-11-13`. This session cannot create them for you. Each run is a cloud agent and bills to your Cursor account.

Point every automation at:

- Repository: `shadybrook/certarig-platform`
- Branch: `product/agent-lifecycle-2026-11-13`
- Tools: Memories, pull requests, computer use
- Slack: leave off until you want the pull-request link in a channel you name

Times are Asia/Kolkata (IST, UTC+5:30). If the scheduler asks for UTC, use the cron line. Weekdays only.

## 1. Listener

- Name: `CertaRig listener`
- When: 08:00 IST, Monday to Friday. Cron: `30 2 * * 1-5`
- Prompt:

```text
Follow company/agents/listener.md exactly. Today is the calendar date in Asia/Kolkata. Read company/COMPANY.md, company/channels.md, and company/HANDOFF.md before you search. Open the daily pull request the handoff describes. Do not publish, send, or change product code.
```

## 2. GTM

- Name: `CertaRig GTM`
- When: 08:40 IST, Monday to Friday. Cron: `10 3 * * 1-5`
- Prompt:

```text
Follow company/agents/gtm.md exactly. Today is the calendar date in Asia/Kolkata. Read the open pull request titled CertaRig daily plus that date, then write gtm.md onto that branch. If the listener file is missing, say so and use only company/COMPANY.md. Do not contact anyone.
```

## 3. Marketing desk

- Name: `CertaRig marketing desk`
- When: 09:20 IST, Monday to Friday. Cron: `50 3 * * 1-5`
- Prompt:

```text
Follow company/agents/marketing-desk.md exactly. Today is the calendar date in Asia/Kolkata. Add company/runs/YYYY-MM-DD/content-pack.md to the open daily pull request. Use only facts in company/COMPANY.md. Do not publish the pack and do not link a site that is not the GitHub repository.
```

## 4. Source finder

- Name: `CertaRig source finder`
- When: 10:00 IST on Monday and Thursday. Cron: `30 4 * * 1,4`
- Prompt:

```text
Follow company/agents/source-finder.md exactly. Today is the calendar date in Asia/Kolkata. Add sources.md to today's daily pull request when it exists. Draft notes only. Do not email, message, or collect personal addresses.
```

## 5. Claim keeper

- Name: `CertaRig claim keeper`
- When: 10:00 IST on Friday. Cron: `30 4 * * 5`
- Prompt:

```text
Follow company/agents/claim-keeper.md exactly. Today is the calendar date in Asia/Kolkata. Review this week's drafts against the product files named in that prompt. Add claims.md to Friday's daily pull request. Do not publish.
```

Turn on 1, 2, and 3 first. Add 4 in the same week if you want unsent notes. Add 5 once a week of drafts exists. Memories stay on so each automation can avoid repeating its own last run. The shared record is still the pull request, because memories are not shared across automations.

## Later, not created yet

Add these only after a week of drafts is worth keeping.

- Demo producer. A script of the five-minute path in `docs/product/AGENT_LIFECYCLE.md`: simulated benches, independent review, an access refusal, and revoke. Fixture runs stay labelled as fixtures.
- Site editor. Copy pull requests against `cursor/certarig-marketing-site-a496` only after you say that branch is the page to keep. It does not deploy.
- Supplier and lab scout. Public drawings and courses for the under-₹3,000 reference bench and for CR-EXT-R1. It drafts questions. It does not order parts.

## Your morning

Open the pull request titled `CertaRig daily` plus today's date. Cut any sentence the claim review marks as ahead of the evidence. Publish or send only what you still mean. Merge the pull request when you want that day's files kept on the branch the next run reads.
