# Sports Lover Agent

A starter service for collecting sports-related articles and video links from RSS/Atom feeds, filtering them, and placing them in a review queue before any Facebook publishing.

## Current MVP

- Reads RSS/Atom feeds configured by the project owner.
- Filters entries using a starter sports-keyword list.
- Classifies items as article or video link.
- Stores unique items in SQLite.
- Provides API endpoints to ingest, review, approve, reject, and (when explicitly enabled) publish approved link posts.
- Keeps Facebook publishing disabled by default.

## Project structure

- app/agents: ingestion workflow
- app/processing: sports filtering and content classification
- app/publishing: guarded Facebook publishing adapter
- app/sources: RSS/Atom reader
- app/database.py: SQLite storage
- app/main.py: FastAPI API
- config: environment settings
- tests: starter tests

## Run locally

1. Create a virtual environment and install dependencies using `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Add permitted RSS/Atom feed URLs to `SPORTS_FEEDS` as a JSON array, for example `SPORTS_FEEDS=[\"https://example.com/sports/rss\"]`. Replace the example with a real feed URL you are allowed to use.
4. Start the API using `uvicorn app.main:app --reload`.
5. Open `http://127.0.0.1:8000/docs`.

## API

- `GET /health` — health check
- `POST /api/ingest` — fetch configured feeds
- `GET /api/items` — list stored items
- `GET /api/items?status=pending` — list items awaiting review
- `POST /api/items/{id}/approve` — approve an item
- `POST /api/items/{id}/reject` — reject an item
- `POST /api/items/{id}/publish` — publish an approved link post if Facebook publishing is configured and enabled

## Facebook publishing safety

Publishing is OFF by default. Keep it off until a Facebook Page, valid Page access token, and required Meta permissions are configured and tested. Never commit `.env`, access tokens, or API keys. The initial MVP publishes links only; it does not download or re-upload third-party video files.

## Limitations and next steps

- Feed URLs must be configured by the owner; no source is assumed to be available or authorized by default.
- Video entries are stored as links/metadata; direct video upload is not implemented.
- Keyword filtering is a starter rule, not a complete sports classifier.
- Add source-specific adapters, scheduling, richer moderation, and Meta's current publishing requirements after the basic service is tested.
