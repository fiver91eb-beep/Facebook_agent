# Sports Lover Agent

GitHub Actions based sports-news video creator and Buffer publisher.

## What it does

- Collects sports headlines from configured RSS feeds every two hours.
- Creates an original vertical 12-second MP4 animated text/news-card video.
- Uploads each MP4 as a public GitHub Release asset (the repository must be public).
- Verifies that the release URL can be fetched publicly.
- Queues the video as a native media post through the connected Facebook Page in Buffer.
- Enforces a maximum of 10 videos queued per UTC day and avoids re-queuing the same source URL.
- Runs automatically every two hours; manual runs are available from **Actions → Sports Lover Agent - Buffer Native Videos → Run workflow**.

**Important:** These are original animated sports-news cards, not match footage, highlights, or AI-generated live sports footage. The agent queues up to 10 videos per UTC day only when enough new sports stories are available. It does not fabricate sports news. Buffer's queue schedule determines the actual publication times.

## Required secret

Open **Settings → Secrets and variables → Actions → New repository secret** and ensure this secret exists:

- `BUFFER_API_KEY` — your Buffer API key.

Do not put tokens in code, commits, issues, or chat. If an API key was exposed, revoke it and create a new one.

The workflow uses GitHub's built-in `GITHUB_TOKEN` to create public Release assets; no Facebook Page ID or Facebook access token is required. It discovers the connected Facebook channel through Buffer. If multiple active Facebook Pages are connected, the script stops rather than choosing the wrong Page.

## Verify

1. Open the repository's **Actions** tab.
2. Select **Sports Lover Agent - Buffer Native Videos**.
3. Press **Run workflow**.
4. Open the latest run and inspect the logs.
5. A successful queue step prints `Buffer confirmed native video post queued` with a Buffer post ID.
6. Open Buffer and check the Facebook Page queue. After the scheduled time, check the Facebook Page/Reels area to confirm publication.

A Buffer queue confirmation means Buffer accepted the post; it does not prove Facebook has published it yet. Check the Buffer post status for the final result.

## Media hosting and copyright

Buffer's API does not accept direct binary media uploads. It fetches videos from public URLs, and those URLs must remain reachable until the scheduled post publishes. This agent stores each MP4 as a public GitHub Release asset so Buffer can fetch it later.

The video cards are original designs based on sports headlines and summaries. The agent does not download or repost broadcast footage or third-party match highlights. Each post includes its source link.

## Main files

- `scripts/collect_github.py` — sports RSS collection and deduplication.
- `scripts/create_and_upload.py` — renders MP4, hosts it in GitHub Releases, and queues it through Buffer.
- `.github/workflows/sports-agent.yml` — scheduled/manual automation.
- `data/pending_posts.json` — collected sports stories.
- `data/video_upload_history.json` — successful Buffer queue history and daily-limit tracking.


## Feel One Turkish drama shorts publisher

The former scheduled sports-news publisher is disabled. The new workflow is **Feel One Turkish Drama Shorts - Buffer Publisher**.

- Processes up to **5 creator-authorized videos per Pakistan calendar day** from data/drama_videos.json.
- Requires each entry to have rights_confirmed: true, a creator/source post URL, and a direct, authorized MP4 URL.
- Preserves the source video's audio/music and adds a small Feel One label; it does not remove another creator's watermark.
- Queues Facebook Reels through the existing Buffer connection. Exactly one active Facebook channel must be connected in Buffer; check it is the intended **Sports Lover** Page before enabling the workflow.
- Deduplicates by source post URL and stores queue history in data/drama_upload_history.json.

### Add approved videos

Replace the example entry in data/drama_videos.json with up to five entries containing title, mood (romantic/sad/emotional), source_url, video_url (direct MP4), rights_confirmed (must be true), and optional caption.

A TikTok/Instagram webpage URL is not a direct MP4 URL. Do not mark a video as authorized unless the creator or rights holder has granted reuse permission for Facebook. A platform's download button alone does not grant reposting rights.

### Run

Open Actions → Feel One Turkish Drama Shorts - Buffer Publisher → Run workflow. Check the logs for each Buffer confirmed Feel One video queued message, then verify the post in Buffer and Facebook. A queued post is not yet proof that Facebook published it.

Required repository secret: BUFFER_API_KEY. The workflow uses GitHub's built-in GITHUB_TOKEN for release assets. Do not place API keys in source files.
