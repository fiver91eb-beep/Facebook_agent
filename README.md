# Sports Lover Agent — GitHub-only edition

This version uses GitHub Actions as the automation runner. It does not require Render or a continuously running server.

## What it does

1. Runs the sports collector every 6 hours (or manually from the Actions tab).
2. Reads the configured RSS feeds in `scripts/collect_github.py`.
3. Filters stories into Cricket, Football, Tennis, Basketball, Formula 1, and Other sports.
4. Labels matching links as article or video-link candidates.
5. Saves new items in `data/pending_posts.json` and commits the updated file to this repository.
6. You approve posts by copying their exact URL into `data/approved_urls.txt`.
7. You manually run **Actions → Publish Approved Sports Links → Run workflow**. The workflow sends approved links to the Buffer queue and records URLs already queued to prevent repeat submissions.

## GitHub-only setup

### 1. Enable Actions write permission

In the repository, open **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**, then save.

### 2. Add Buffer secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `BUFFER_API_KEY`: your Buffer API key.
- `BUFFER_CHANNEL_ID`: the ID of the Facebook Page channel connected in Buffer.

Never put these credentials in source files, commits, issues, or chat. If a secret is exposed, revoke and replace it.

### 3. Collect content

Open **Actions → Collect Sports Content → Run workflow** to run it immediately. Otherwise the schedule runs every six hours. GitHub scheduled workflows can be delayed during busy periods and run from the default branch.

After it completes, open `data/pending_posts.json` to review the collected links.

### 4. Approve and queue content

Edit `data/approved_urls.txt` on GitHub and add one exact URL per line. Commit the change. Then open **Actions → Publish Approved Sports Links → Run workflow**.

A successful run means Buffer accepted the link into its queue; it does not mean Facebook has already published it. Buffer controls the actual queue schedule.

## Content rules

- Categories and keyword conditions are in `SPORTS` inside `scripts/collect_github.py`.
- Feed URLs are in `FEEDS` in the same file.
- The classifier is keyword-based, not AI-based.
- Video detection only identifies likely video links from URL/text hints. It does not download or upload video files.
- Only publish content you have permission to share and comply with each source's and platform's terms.

## Important GitHub limitations

- GitHub Actions is a scheduled/on-demand job runner, not an always-on backend host.
- This GitHub-only version does **not** provide a live dashboard or a continuously available HTTP API.
- Collection and publishing happen only when their respective workflows run.
- Collected and published URL history is stored in repository JSON files. Keep the repository private if the collected data should not be public.
- The Buffer GraphQL request is implemented but must be verified with your own Buffer account and secrets before relying on it.

## Main files

- `scripts/collect_github.py` — RSS collection, category filtering, deduplication, article/video-link classification.
- `scripts/publish_approved.py` — sends manually approved links to Buffer.
- `.github/workflows/collect-sports.yml` — scheduled/manual collector.
- `.github/workflows/publish-approved.yml` — manual publisher.
- `data/pending_posts.json` — collected content waiting for review.
- `data/approved_urls.txt` — URLs approved by the owner.
- `data/published_urls.json` — URLs already accepted by Buffer.

The older FastAPI/Render prototype files remain in the repository but are not used by these GitHub Actions workflows.
