# Sports Lover Agent

A small FastAPI service for collecting sports articles and video links from RSS/Atom feeds, reviewing them in a protected dashboard, and adding approved link posts to a connected Facebook Page through Buffer.

## Current MVP features

- Reads owner-configured RSS/Atom feeds.
- Filters entries using a starter sports-keyword list.
- Classifies items as article or video link.
- Stores unique source URLs in SQLite.
- Provides a mobile-friendly dashboard to review, approve, reject, and queue content.
- Runs automatic feed collection on a configurable interval (default: every 60 minutes).
- Protects the dashboard, API, and API documentation with HTTP Basic admin authentication.
- Leaves the Render health-check endpoint `/health` public for hosting health checks.
- Uses Buffer's GraphQL API integration; publishing is disabled by default.

## Required server configuration

Set these as environment variables in your hosting provider. Do not put real credentials in GitHub or browser code.

| Variable | Purpose |
| --- | --- |
| `ADMIN_USERNAME` | Required dashboard/API login username |
| `ADMIN_PASSWORD` | Required dashboard/API login password |
| `SPORTS_FEEDS` | JSON array of RSS/Atom feed URLs |
| `AUTO_INGEST_ENABLED` | Enable scheduled collection (`true` / `false`) |
| `INGEST_INTERVAL_SECONDS` | Collection interval; default 3600 seconds |
| `BUFFER_API_KEY` | Secret Buffer API key |
| `BUFFER_CHANNEL_ID` | ID of the intended Facebook Page channel in Buffer |
| `PUBLISH_ENABLED` | Must remain `false` until Buffer is configured and tested |
| `DATABASE_PATH` | SQLite file path; default `data/sports_agent.db` |

Starter feeds are prefilled in the included Render Blueprint and `.env.example`: BBC Sport (all sports, football, cricket), Sky Sports (all sports, cricket, tennis, Formula 1), ESPNcricinfo (cricket), and Formula1.com. Feed addresses can change or temporarily reject requests, so check the dashboard collection result and remove any source that stops working. See the feed list reference: https://www.feeder.co/knowledge-base/rss-content/sports-news-rss-feeds/ (updated November 10, 2026).

Example format for adding or replacing feeds:

```json
["https://example.com/sports/rss.xml","https://example.org/football/feed"]
```

The `SPORTS_FEEDS` environment variable must contain a JSON array, not a comma-separated list.

## Buffer and Facebook setup

1. Connect the intended Facebook Page to your Buffer account.
2. Create a Buffer API key in Buffer Settings → API.
3. Add the API key as the server secret `BUFFER_API_KEY`.
4. Keep `PUBLISH_ENABLED=false` while configuring.
5. Open the protected endpoint `/api/buffer/channels` while logged in and identify the intended Facebook Page channel.
6. Set that channel's ID as `BUFFER_CHANNEL_ID`.
7. Confirm the selected channel is the correct Page and test with a harmless approved link.
8. Only then set `PUBLISH_ENABLED=true`.

A successful API response means Buffer accepted a post into its queue; it does not prove the post has already appeared on Facebook. Buffer publishes according to the channel's queue schedule.

Never share the Buffer API key in chat, screenshots, or GitHub commits. If it is exposed, revoke/rotate it in Buffer.

## Run locally

1. Install dependencies: `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Set a strong `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
4. Add RSS/Atom URLs to `SPORTS_FEEDS`.
5. Start the API: `uvicorn app.main:app --reload`.
6. Open `http://127.0.0.1:8000`; the browser will request the admin username and password.

## API routes

All routes below except `GET /health` require admin authentication.

- `GET /` — dashboard.
- `GET /health` — public hosting health check.
- `GET /api/status` — service, feed, scheduler, and Buffer configuration status.
- `GET /api/buffer/channels` — list Buffer channels available to the configured key.
- `POST /api/ingest` — manually fetch configured feeds.
- `GET /api/items` — list stored items.
- `POST /api/items/{id}/approve` — approve an item.
- `POST /api/items/{id}/reject` — reject an item.
- `POST /api/items/{id}/publish` — add an approved link post to the configured Buffer queue.

## Important limitations and deployment notes

- This MVP queues article/video **links** as Facebook link posts. It does not download third-party videos or upload video files.
- Actual video-media publishing needs a separate workflow using a real, publicly accessible video asset URL and must respect the source's rights and platform rules.
- Keyword filtering is a starter filter, not an AI classifier; it can miss relevant stories or include irrelevant ones.
- RSS feed URLs must be configured by the owner. No feed source is assumed to be authorized by default.
- The automatic collector runs inside the web service. On a free hosting plan that sleeps or restarts, collection pauses while the service is stopped and resumes when it runs again.
- Render free Web Services do not provide persistent disks. SQLite data stored on the service filesystem can be lost on restart, redeploy, or instance replacement. Use a persistent disk on a paid plan or migrate to a managed PostgreSQL database before relying on long-term storage.
- Keep `PUBLISH_ENABLED=false` until the real Buffer key and Facebook Page channel have been verified.
- HTTP Basic authentication protects the dashboard and API. Use the hosted HTTPS URL and a strong unique password. Do not expose the service without setting both admin credentials.

## Deployment

The included `render.yaml` defines a Render Web Service. Connect the GitHub repository in Render and create the service from the Blueprint. Render will ask you to supply the `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `BUFFER_API_KEY`, and `BUFFER_CHANNEL_ID` secrets. Use a unique admin password. Keep publishing disabled initially; configure feeds and Buffer after the service is deployed.

A repository configuration file does not itself deploy the service. Deployment is complete only after Render reports a successful deploy and provides a live service URL.
