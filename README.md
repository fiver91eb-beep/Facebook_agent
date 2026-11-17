# Sports Lover Agent

GitHub Actions based sports-content video publisher.

## Current workflow

- Collects sports headlines from configured RSS feeds every two hours.
- Creates an original vertical 12-second animated text video for a collected sports story.
- Uploads the MP4 as a native Facebook Page video through Meta Graph API.
- Keeps upload history and avoids uploading the same source URL twice.
- Enforces a maximum of 10 successful uploads per UTC day (one scheduled attempt every two hours).
- Manual runs are available from **Actions → Sports Lover Agent - 10 Daily Native Videos → Run workflow**.

**Important:** The current video format is an original animated text/news card. It is not match footage, highlights, or AI-generated live sports footage. The agent can publish up to 10 videos per UTC day when at least 10 new sports stories are available. If fewer new stories are collected, it uploads fewer; it does not invent news.

## Required GitHub Actions secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and add:

1. `FACEBOOK_PAGE_ID` — the numeric ID of the Facebook Page.
2. `FACEBOOK_PAGE_ACCESS_TOKEN` — a Page access token for a person with the Page's **CREATE_CONTENT** task and the required permissions: `pages_manage_posts`, `pages_read_engagement`, and `pages_show_list`.

Do not put tokens in code, commits, issues, or chat. If a token is exposed, revoke it and create a new one.

Meta's Page Videos endpoint is `/{page_id}/videos`. Meta documents that publishing requires a Page access token and the permissions listed above:
https://developers.facebook.com/docs/graph-api/reference/page/videos

## Run and verify

1. Add both secrets.
2. Open the repository's **Actions** tab.
3. Select **Sports Lover Agent - 10 Daily Native Videos**.
4. Press **Run workflow**.
5. Open the run logs. A successful upload prints `Facebook confirmed native video upload` with the returned video ID.
6. Check the Facebook Page's Videos/Reels area to confirm it is visible.

The schedule attempts one upload every two hours. GitHub scheduled workflows can be delayed, so exact posting times are not guaranteed.

## Source and copyright

The system uses sports RSS headlines as source material for original text-based video cards. It does not download or repost broadcast footage or third-party match highlights. A source link is included in the Facebook description for context.

## Main files

- `scripts/collect_github.py` — sports RSS collection and deduplication.
- `scripts/create_and_upload.py` — renders a vertical MP4 and uploads it to the Facebook Page.
- `.github/workflows/sports-agent.yml` — scheduled/manual automation.
- `data/pending_posts.json` — collected sports stories.
- `data/video_upload_history.json` — successful upload history and daily-limit tracking.
