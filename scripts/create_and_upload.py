import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PENDING = DATA / "pending_posts.json"
HISTORY = DATA / "video_upload_history.json"
ENDPOINT = "https://api.buffer.com"
MAX_PER_RUN = int(os.getenv("MAX_VIDEOS_PER_RUN", "1"))
DAILY_LIMIT = 10
REPOSITORY = os.getenv("GITHUB_REPOSITORY", "fiver91eb-beep/Facebook_agent")


def load_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def buffer_request(query, variables, api_key):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=40) as response:
            result = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = getattr(exc, "read", lambda: b"")()
        raise RuntimeError(f"Buffer request failed: {exc}; {detail[:1000]!r}") from exc
    if result.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "GraphQL error") for e in result["errors"]))
    return result.get("data") or {}


def find_facebook_channel(api_key):
    org_data = buffer_request(
        "query { account { organizations { id name } } }", {}, api_key
    )
    organizations = (org_data.get("account") or {}).get("organizations") or []
    matches = []
    channel_query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id name displayName service descriptor isDisconnected isLocked
      }
    }
    """
    for org in organizations:
        data = buffer_request(channel_query, {"organizationId": org["id"]}, api_key)
        for channel in data.get("channels") or []:
            service = (channel.get("service") or "").lower()
            descriptor = (channel.get("descriptor") or "").lower()
            if ("facebook" in service or "facebook" in descriptor) and not channel.get("isDisconnected") and not channel.get("isLocked"):
                matches.append((org.get("name", ""), channel))
    if len(matches) == 1:
        org_name, channel = matches[0]
        label = channel.get("displayName") or channel.get("name") or channel.get("descriptor")
        print(f"Using Facebook channel: {label} ({org_name})")
        return channel["id"]
    if not matches:
        raise SystemExit("No active Facebook Page channel found. Connect the intended Page in Buffer.")
    names = [str(ch.get("displayName") or ch.get("name") or ch.get("descriptor")) for _, ch in matches]
    raise SystemExit("Multiple Facebook Pages found in Buffer: " + ", ".join(names) +
                     ". Keep only the intended Page connected or configure channel selection.")


def font(size, bold=False):
    path = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(path, size) if Path(path).exists() else ImageFont.load_default()


def wrap_words(draw, text, face, max_width):
    lines, current = [], ""
    for word in str(text).split():
        trial = (current + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=face)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_card(item, output):
    width, height = 720, 1280
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / height
        color = (int(8 + 10 * ratio), int(20 + 22 * ratio), int(48 + 45 * ratio))
        draw.line((0, y, width, y), fill=color)

    draw.rounded_rectangle((42, 55, 678, 1225), radius=34, outline=(70, 135, 220), width=3)
    draw.text((78, 105), "SPORTS LOVER  |  DAILY UPDATE", font=font(25, True), fill=(110, 195, 255))
    draw.rounded_rectangle((78, 190, 360, 246), radius=18, fill=(18, 95, 145))
    category = (item.get("category") or "SPORTS").upper()
    draw.text((98, 202), category[:22], font=font(23, True), fill="white")

    title = item.get("title") or "Today's Sports Update"
    y = 320
    for line in wrap_words(draw, title, font(43, True), 550)[:6]:
        draw.text((78, y), line, font=font(43, True), fill="white")
        y += 60

    summary = item.get("summary") or "Follow the latest sports stories and updates."
    y = max(y + 45, 760)
    for line in wrap_words(draw, summary, font(27), 550)[:8]:
        draw.text((80, y), line, font=font(27), fill=(205, 220, 240))
        y += 42

    draw.line((78, 1080, 642, 1080), fill=(70, 135, 220), width=2)
    draw.text((78, 1110), "Follow Sports Lover for more updates", font=font(24, True), fill=(110, 195, 255))
    draw.text((78, 1160), "Source link is included in caption", font=font(18), fill=(165, 180, 205))
    image.save(output, quality=92)


def make_video(card, output):
    command = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(card),
        "-t", "12", "-vf",
        "scale=800:1422,zoompan=z='min(zoom+0.0007,1.035)':d=360:s=720x1280:fps=30,format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
        "-movflags", "+faststart", str(output)
    ]
    subprocess.run(command, check=True, capture_output=True)


def publish_release_asset(video_path, asset_name, release_tag, github_token):
    if not github_token:
        raise SystemExit("GitHub Actions did not provide GITHUB_TOKEN.")
    env = os.environ.copy()
    env["GH_TOKEN"] = github_token

    check = subprocess.run(
        ["gh", "release", "view", release_tag, "--repo", REPOSITORY],
        env=env, text=True, capture_output=True
    )
    if check.returncode != 0:
        create = subprocess.run(
            ["gh", "release", "create", release_tag, "--repo", REPOSITORY,
             "--title", f"Sports Lover videos {release_tag}",
             "--notes", "Generated sports news-card videos used by the Sports Lover publishing agent."],
            env=env, text=True, capture_output=True
        )
        if create.returncode != 0:
            raise RuntimeError("Could not create GitHub media release: " + create.stderr[-1500:])

    upload = subprocess.run(
        ["gh", "release", "upload", release_tag, str(video_path),
         "--repo", REPOSITORY, "--clobber"],
        env=env, text=True, capture_output=True
    )
    if upload.returncode != 0:
        raise RuntimeError("Could not upload video to GitHub Release: " + upload.stderr[-1500:])

    return f"https://github.com/{REPOSITORY}/releases/download/{release_tag}/{asset_name}"


def verify_public_video_url(url):
    response = requests.get(url, headers={"Range": "bytes=0-1023"},
                            allow_redirects=True, timeout=45, stream=True)
    try:
        if response.status_code not in (200, 206):
            raise RuntimeError(f"Public video URL check failed: HTTP {response.status_code}")
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" in content_type:
            raise RuntimeError("GitHub Release URL returned HTML instead of a video file.")
    finally:
        response.close()


def queue_video_in_buffer(item, video_url, channel_id, api_key):
    text = (
        (item.get("title") or "Sports Update")[:180]
        + "\\n\\n" + (item.get("summary") or "")[:1200]
        + "\\n\\nSource: " + (item.get("url") or "")
        + "\\nOriginal Sports Lover animated news card."
    )
    mutation = """
    mutation QueueSportsVideo($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text dueAt assets { id mimeType } } }
        ... on MutationError { message }
      }
    }
    """
    data = buffer_request(mutation, {"input": {
        "text": text,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
        "assets": [{"video": {"url": video_url}}],
    }}, api_key)
    result = data.get("createPost") or {}
    if result.get("message") or not result.get("post"):
        raise RuntimeError(result.get("message") or "Buffer did not confirm that the video was queued.")
    return result["post"]


def main():
    api_key = os.getenv("BUFFER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing BUFFER_API_KEY GitHub Actions secret. Add it in repository Actions secrets.")
    channel_id = find_facebook_channel(api_key)

    posts = load_json(PENDING, [])
    history = load_json(HISTORY, [])
    today = datetime.now(timezone.utc).date().isoformat()
    uploaded_today = sum(1 for row in history if row.get("queued_at", "").startswith(today))
    if uploaded_today >= DAILY_LIMIT:
        print(f"Daily queue limit reached: {uploaded_today}/{DAILY_LIMIT} videos (UTC).")
        return

    queued_urls = {row.get("url") for row in history}
    candidates = [
        item for item in reversed(posts)
        if item.get("url") and item["url"] not in queued_urls and item.get("title")
    ][:min(MAX_PER_RUN, DAILY_LIMIT - uploaded_today)]
    if not candidates:
        print("No new sports stories are waiting. No video was queued.")
        return

    release_tag = "sports-media-" + today.replace("-", "")
    temp = DATA / "generated"
    temp.mkdir(parents=True, exist_ok=True)
    github_token = os.getenv("GITHUB_TOKEN", "")

    for index, item in enumerate(candidates, start=1):
        digest = hashlib.sha256(item["url"].encode()).hexdigest()[:12]
        asset_name = f"sports-{today}-{digest}.mp4"
        card = temp / f"{digest}.jpg"
        video = temp / asset_name
        render_card(item, card)
        make_video(card, video)

        video_url = publish_release_asset(video, asset_name, release_tag, github_token)
        verify_public_video_url(video_url)
        post = queue_video_in_buffer(item, video_url, channel_id, api_key)

        history.append({
            "url": item["url"],
            "title": item.get("title", ""),
            "category": item.get("category", "sports"),
            "buffer_post_id": post.get("id"),
            "video_url": video_url,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "status": "queued_in_buffer",
        })
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        print(f"Buffer confirmed native video post queued: {post.get('id')} | dueAt={post.get('dueAt')} | {item.get('title', '')}")
        card.unlink(missing_ok=True)
        video.unlink(missing_ok=True)

    print(f"Videos queued this run: {len(candidates)} | Daily total: {uploaded_today + len(candidates)}/{DAILY_LIMIT}")
    print("Note: Buffer queue confirmation is not the same as Facebook publication confirmation.")


if __name__ == "__main__":
    main()
