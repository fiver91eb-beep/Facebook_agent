import json
import os
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PENDING = DATA / "pending_posts.json"
HISTORY = DATA / "video_upload_history.json"
MAX_PER_RUN = int(os.getenv("MAX_VIDEOS_PER_RUN", "1"))
DAILY_LIMIT = 10
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v27.0")


def load_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrap_words(draw, text, face, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
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
    pixels = image.load()
    for y in range(height):
        ratio = y / height
        color = (int(8 + 10 * ratio), int(20 + 22 * ratio), int(48 + 45 * ratio))
        for x in range(width):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((42, 55, 678, 1225), radius=34, outline=(70, 135, 220), width=3)
    draw.text((78, 105), "SPORTS LOVER  |  DAILY UPDATE", font=font(25, True), fill=(110, 195, 255))
    draw.rounded_rectangle((78, 190, 310, 246), radius=18, fill=(18, 95, 145))
    category = (item.get("category") or "SPORTS").upper()
    draw.text((98, 202), category[:18], font=font(23, True), fill="white")

    title = item.get("title") or "Today's Sports Update"
    title_lines = wrap_words(draw, title, font(46, True), 550)[:6]
    y = 320
    for line in title_lines:
        draw.text((78, y), line, font=font(46, True), fill=(255, 255, 255))
        y += 62

    summary = item.get("summary") or "Follow the latest sports stories and updates."
    summary_lines = wrap_words(draw, summary, font(28), 550)[:8]
    y = max(y + 45, 760)
    for line in summary_lines:
        draw.text((80, y), line, font=font(28), fill=(205, 220, 240))
        y += 43

    draw.line((78, 1080, 642, 1080), fill=(70, 135, 220), width=2)
    draw.text((78, 1110), "Follow Sports Lover for more updates", font=font(24, True), fill=(110, 195, 255))
    draw.text((78, 1160), "Source link in post description", font=font(18), fill=(165, 180, 205))
    image.save(output, quality=95)


def make_video(card, output):
    command = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(card),
        "-t", "12", "-vf",
        "scale=800:1422,zoompan=z='min(zoom+0.0007,1.035)':d=360:s=720x1280:fps=30,format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
        "-movflags", "+faststart", str(output)
    ]
    subprocess.run(command, check=True, capture_output=True)


def upload_video(video_path, item, page_id, token):
    endpoint = f"https://graph-video.facebook.com/{GRAPH_VERSION}/{page_id}/videos"
    description = (
        (item.get("summary") or "")[:1800]
        + "\n\nSource: " + item.get("url", "")
        + "\nVisual: original Sports Lover text animation. News source is linked for context."
    )
    with video_path.open("rb") as video_file:
        response = requests.post(
            endpoint,
            data={
                "access_token": token,
                "title": (item.get("title") or "Sports Update")[:100],
                "description": description,
                "published": "true",
            },
            files={"source": (video_path.name, video_file, "video/mp4")},
            timeout=300,
        )
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"Facebook returned non-JSON response: HTTP {response.status_code}")
    if not response.ok or not payload.get("id"):
        raise RuntimeError(f"Facebook upload failed (HTTP {response.status_code}): {payload}")
    return payload["id"]


def main():
    page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not token:
        raise SystemExit(
            "Missing FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN GitHub Actions secret."
        )

    posts = load_json(PENDING, [])
    history = load_json(HISTORY, [])
    today = datetime.now(timezone.utc).date().isoformat()
    uploaded_today = sum(1 for row in history if row.get("uploaded_at", "").startswith(today))
    if uploaded_today >= DAILY_LIMIT:
        print(f"Daily limit reached: {uploaded_today}/{DAILY_LIMIT} videos (UTC).")
        return

    uploaded_urls = {row.get("url") for row in history}
    candidates = [
        item for item in reversed(posts)
        if item.get("url") and item["url"] not in uploaded_urls and item.get("title")
    ][:min(MAX_PER_RUN, DAILY_LIMIT - uploaded_today)]

    if not candidates:
        print("No new sports stories are waiting. No video uploaded.")
        return

    temp = DATA / "generated"
    temp.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(candidates, start=1):
        safe_name = f"sports_update_{today}_{uploaded_today + index:02d}"
        card = temp / f"{safe_name}.jpg"
        video = temp / f"{safe_name}.mp4"
        render_card(item, card)
        make_video(card, video)
        video_id = upload_video(video, item, page_id, token)
        history.append({
            "url": item["url"],
            "title": item.get("title", ""),
            "category": item.get("category", "sports"),
            "facebook_video_id": video_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
        HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Facebook confirmed native video upload: {video_id} | {item.get('title', '')}")
        card.unlink(missing_ok=True)
        video.unlink(missing_ok=True)

    print(f"Uploaded this run: {len(candidates)} | Daily total: {uploaded_today + len(candidates)}/{DAILY_LIMIT}")


if __name__ == "__main__":
    main()
