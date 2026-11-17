# Sports Lover Agent

A FastAPI service for collecting sports-related articles and video links from configured RSS/Atom feeds, reviewing them, and adding approved link posts to a connected Facebook Page through Buffer.

## Current MVP

- Reads owner-configured RSS/Atom feeds.
- Filters entries using a starter sports-keyword list.
- Classifies items as article or video link.
- Stores unique items in SQLite.
- Provides a dashboard and API to collect, review, approve, reject, and queue approved posts.
- Uses the current Buffer GraphQL API (not the legacy Buffer API and not the Facebook Graph API directly).
- Publishing is disabled by default.

## Configure Buffer

1. Connect the intended Facebook Page to your Buffer account.
2. Create a Buffer API key in Buffer Settings → API.
3. Set `BUFFER_API_KEY` as a server environment secret. Never commit it to GitHub or put it in browser code.
4. Temporarily leave `PUBLISH_ENABLED=false` and open `/api/buffer/channels` on the deployed service to list connected Buffer channels.
5. Find the Facebook Page channel and copy its `id` into the server secret `BUFFER_CHANNEL_ID`.
6. Set `PUBLISH_ENABLED=true` only after confirming the channel ID is the correct Facebook Page.

The API key can access the Buffer account's organizations and channels. Keep it private and rotate it if it is exposed.

## Environment variables

- `SPORTS_FEEDS`: JSON array of permitted RSS/Atom feed URLs.
- `BUFFER_API_KEY`: Buffer API key (server-side secret).
- `BUFFER_CHANNEL_ID`: ID of the intended Facebook Page channel in Buffer.
- `PUBLISH_ENABLED`: must be `true` to allow publishing; defaults to `false`.
- `DATABASE_PATH`: SQLite database path.

See `.env.example` for the complete list.

## Run locally

1. Install dependencies: `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Add feed URLs and server credentials to `.env`.
4. Start the API: `uvicorn app.main:app --reload`.
5. Open `http://127.0.0.1:8000`.

## API

- `GET /health` — health check.
- `GET /api/status` — service and Buffer configuration status.
- `GET /api/buffer/channels` — list channels available to the configured Buffer key.
- `POST /api/ingest` — fetch configured feeds.
- `GET /api/items` — list stored items.
- `POST /api/items/{id}/approve` — approve an item.
- `POST /api/items/{id}/reject` — reject an item.
- `POST /api/items/{id}/publish` — add an approved link post to the configured Buffer channel queue.

## Important limitations

- This MVP queues article/video **links** as Facebook link posts. It does not download third-party videos or upload video files.
- Buffer's API supports media via public links, but actual video-media publishing needs a separate media-asset workflow and a compatible public video URL. A normal webpage URL is not itself a video file.
- RSS feed URLs must be configured by the owner; no source is assumed to be authorized by default.
- Keyword filtering is a starter rule, not a complete sports classifier.
- A successful publish API response means Buffer accepted the post into its queue. It does not mean the Facebook post has already been published. Buffer will publish according to the channel queue schedule.

## Security

Never commit `.env`, Buffer API keys, or other credentials. Configure secrets in the hosting provider's environment-variable settings.
