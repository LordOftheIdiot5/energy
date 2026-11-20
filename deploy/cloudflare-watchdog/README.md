# Independent Nordl Energy watchdog
Cloudflare Cron every 15 minutes (UTC :02/:17/:32/:47). Checks the actual public energy JSON (2 MB limit, currently ~95 KB); no map archives. At snapshot age 90 minutes, or two consecutive failed reads, request guarded GitHub recovery only if no existing active fetch; 30-minute attempted-dispatch cooldown. At 110 minutes, or two failed reads, alert the private operator Telegram chat. Reminders at most every two hours after successful delivery; send recovery once age is under 70 minutes. Durable Object keeps state across invocations; no public HTTP endpoint. Notifications are at-least-once, not exactly-once if a response is lost. GitHub workflow concurrency and freshness guard remain the final defense against overlap. Snapshot generation is not a guarantee of freshness of every underlying series.
## Deploy only after PR is merged and CI is green
From the repository root, cd deploy/cloudflare-watchdog. Use a Cloudflare-authorized terminal:
```
npx wrangler@4 login
npx wrangler@4 deploy
npx wrangler@4 secret put GITHUB_DISPATCH_TOKEN
npx wrangler@4 secret put TELEGRAM_BOT_TOKEN
npx wrangler@4 secret put TELEGRAM_CHAT_ID
npx wrangler@4 tail
```
Deploy creates a Worker + SQLite Durable Object + Cron. Check account plan/usage first. Credentials entered interactively, never in Git, CLI arguments, chat or logs. Fine-grained GitHub PAT limited to energy repository, Actions read/write only; expiration and rotation documented by operator. Use an explicitly approved private operator chat, not public NordlOfficial channel unless intentionally approved. Bot must be allowed to send there. Deploy before secrets may produce harmless missing-secret errors until configured; no dispatch or notification without respective secret. Verify scheduled invocation in Cloudflare logs, then validate Telegram delivery using a controlled test on an isolated worker or consenting operator chat; do not simulate stale production by changing timestamps. Verify recovery from a genuinely delayed public snapshot and GitHub workflow dispatch with recovery=true. GitHub scheduling and execution are separate from VPS; this worker also does not require the VPS, but still depends on GitHub availability for collection. A complete GitHub outage requires separate collector/hosting architecture; not claimed here. No credentials or Cloudflare provisioning performed by CI.
