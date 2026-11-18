import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
QUEUE = DATA / "drama_videos.json"
HISTORY = DATA / "drama_upload_history.json"
ENDPOINT = "https://api.buffer.com"
TZ = ZoneInfo("Asia/Karachi")
DAILY_LIMIT = 5
REPOSITORY = os.getenv("GITHUB_REPOSITORY", "fiver91eb-beep/Facebook_agent")


def buffer_request(query, variables, api_key):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
    })
    try:
        with urlopen(req, timeout=40) as response:
            result = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = getattr(exc, "read", lambda: b"")()
        raise RuntimeError(f"Buffer request failed: {exc}; {detail[:800]!r}") from exc
    if result.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "GraphQL error") for e in result["errors"]))
    return result.get("data") or {}


def find_facebook_channel(api_key):
    data = buffer_request("query { account { organizations { id name } } }", {}, api_key)
    matches = []
    query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id name displayName service descriptor isDisconnected isLocked
      }
    }"""
    for org in (data.get("account") or {}).get("organizations") or []:
        result = buffer_request(query, {"organizationId": org["id"]}, api_key)
        for channel in result.get("channels") or []:
            label = " ".join(str(channel.get(k) or "") for k in ("service", "descriptor", "displayName", "name")).lower()
            if "facebook" in label and not channel.get("isDisconnected") and not channel.get("isLocked"):
                matches.append((org.get("name", ""), channel))
    if len(matches) != 1:
        labels = [c.get("displayName") or c.get("name") or c.get("descriptor") for _, c in matches]
        raise SystemExit("Expected exactly one active Facebook channel in Buffer; found: " + str(labels))
    org, channel = matches[0]
    print(f"Selected connected Facebook channel: {channel.get('displayName') or channel.get('name')} ({org})")
    return channel["id"]


def download_video(url, target):
    response = requests.get(url, stream=True, timeout=60, headers={"User-Agent": "FeelOnePublisher/1.0"})
    try:
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" in content_type:
            raise RuntimeError("Source URL returned a webpage, not a video file.")
        with target.open("wb") as out:
            for chunk in response.iter_content(1024 * 256):
                if chunk:
                    out.write(chunk)
    finally:
        response.close()
    if not target.exists() or target.stat().st_size < 20_000:
        raise RuntimeError("Downloaded file is empty or too small to be a valid video.")


def brand_video(source, target, title):
    safe = "Feel One"
    # Preserve source audio/music. Only add a small, unobtrusive page label.
    vf = "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,drawtext=text='Feel One':fontcolor=white:fontsize=26:box=1:boxcolor=black@0.45:boxborderw=12:x=(w-text_w)/2:y=h-100"
    command = ["ffmpeg", "-y", "-i", str(source), "-vf", vf, "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", str(target)]
    subprocess.run(command, check=True, capture_output=True)
    if not target.exists() or target.stat().st_size < 20_000:
        raise RuntimeError("FFmpeg did not produce a usable video.")


def publish_asset(path, name, tag, token):
    if not token:
        raise SystemExit("Missing GitHub Actions GITHUB_TOKEN.")
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    view = subprocess.run(["gh", "release", "view", tag, "--repo", REPOSITORY], env=env, capture_output=True, text=True)
    if view.returncode:
        made = subprocess.run(["gh", "release", "create", tag, "--repo", REPOSITORY,
                               "--title", f"Feel One media {tag}",
                               "--notes", "Creator-authorized Feel One short-form videos."],
                              env=env, capture_output=True, text=True)
        if made.returncode:
            raise RuntimeError("Could not create media release: " + made.stderr[-1000:])
    uploaded = subprocess.run(["gh", "release", "upload", tag, str(path), "--repo", REPOSITORY, "--clobber"],
                              env=env, capture_output=True, text=True)
    if uploaded.returncode:
        raise RuntimeError("Could not upload media asset: " + uploaded.stderr[-1000:])
    return f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"


def queue_post(item, video_url, channel_id, api_key):
    caption = (item.get("caption") or item["title"])[:1800]
    mutation = """
    mutation QueueFeelOneVideo($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text dueAt } }
        ... on MutationError { message }
      }
    }"""
    data = buffer_request(mutation, {"input": {
        "text": caption + "\n\n#TurkishDrama #FeelOne #DramaShorts",
        "channelId": channel_id, "schedulingType": "automatic", "mode": "addToQueue",
        "metadata": {"facebook": {"type": "reel"}},
        "assets": [{"video": {"url": video_url}}],
    }}, api_key)
    result = data.get("createPost") or {}
    if result.get("message") or not result.get("post"):
        raise RuntimeError(result.get("message") or "Buffer did not confirm queueing.")
    return result["post"]


def main():
    api_key = os.getenv("BUFFER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing BUFFER_API_KEY GitHub Actions secret.")
    if not QUEUE.exists():
        raise SystemExit("Missing data/drama_videos.json.")
    items = json.loads(QUEUE.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    now = datetime.now(timezone.utc)
    today = now.astimezone(TZ).date()
    count_today = 0
    for row in history:
        try:
            dt = datetime.fromisoformat(row["queued_at"])
            if dt.astimezone(TZ).date() == today:
                count_today += 1
        except (KeyError, TypeError, ValueError):
            pass
    remaining = max(0, DAILY_LIMIT - count_today)
    if not remaining:
        print(f"Pakistan daily limit reached: {count_today}/{DAILY_LIMIT}")
        return
    done = {row.get("source_url") for row in history}
    candidates = [x for x in items if x.get("rights_confirmed") is True
                  and x.get("source_url") and x.get("video_url") and x.get("title")
                  and x["source_url"] not in done]
    if not candidates:
        print("No new creator-authorized videos found. Nothing was downloaded or posted.")
        return
    channel_id = find_facebook_channel(api_key)
    temp = DATA / "drama_work"
    temp.mkdir(parents=True, exist_ok=True)
    tag = "feel-one-media-" + today.strftime("%Y%m%d")
    token = os.getenv("GITHUB_TOKEN", "")
    queued = 0
    for item in candidates[:remaining]:
        digest = hashlib.sha256(item["source_url"].encode()).hexdigest()[:12]
        raw, final = temp / f"{digest}-source.mp4", temp / f"feel-one-{digest}.mp4"
        try:
            download_video(item["video_url"], raw)
            brand_video(raw, final, item["title"])
            name = final.name
            url = publish_asset(final, name, tag, token)
            post = queue_post(item, url, channel_id, api_key)
            history.append({"source_url": item["source_url"], "title": item["title"],
                            "mood": item.get("mood", "romantic"), "video_url": url,
                            "buffer_post_id": post.get("id"),
                            "queued_at": datetime.now(timezone.utc).isoformat(),
                            "status": "queued_in_buffer"})
            HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            queued += 1
            print(f"Buffer confirmed Feel One video queued: {post.get('id')} | {item['title']}")
        finally:
            raw.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
    print(f"Queued this run: {queued}; Pakistan daily total: {count_today + queued}/{DAILY_LIMIT}")
    print("Buffer queue confirmation is not proof Facebook has published the Reel yet.")


if __name__ == "__main__":
    main()
