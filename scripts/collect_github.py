import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PENDING = DATA / "pending_posts.json"
FEEDS = [
    "https://feeds.bbci.co.uk/sport/rss.xml",
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "https://www.skysports.com/rss/12040",
    "https://www.skysports.com/rss/12123",
    "https://www.skysports.com/rss/12110",
    "https://www.skysports.com/rss/12433",
    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
    "https://www.formula1.com/en/latest/all.xml",
]
SPORTS = {
    "cricket": ["cricket", "ipl", "psl", "test match", "odi", "t20", "world cup"],
    "football": ["football", "soccer", "premier league", " champions league", "fifa", "uefa"],
    "tennis": ["tennis", "wimbledon", "atp", "wta", "french open", "us open"],
    "basketball": ["basketball", "nba", "wnba"],
    "formula1": ["formula 1", "formula one", "f1", "grand prix"],
    "other": ["sports", "olympics", "athletics", "rugby", "hockey", "boxing"],
}
VIDEO_HINTS = ["youtube.com/watch", "youtu.be/", "vimeo.com/", ".mp4", ".mov", "video"]
MAX_PER_FEED = int(os.getenv("MAX_ITEMS_PER_FEED", "25"))

def classify(text: str) -> tuple[str, str] | None:
    value = text.lower()
    for category, words in SPORTS.items():
        if any(word.strip() in value for word in words):
            kind = "video" if any(hint in value for hint in VIDEO_HINTS) else "article"
            return category, kind
    return None

def main():
    DATA.mkdir(exist_ok=True)
    old = json.loads(PENDING.read_text(encoding="utf-8")) if PENDING.exists() else []
    known = {item.get("url") for item in old}
    added = []
    errors = []
    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if getattr(feed, "bozo", False) and not feed.entries:
                errors.append(f"Feed parse failed: {feed_url}")
                continue
            for entry in feed.entries[:MAX_PER_FEED]:
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "") or "")
                summary = re.sub(r"\s+", " ", summary).strip()[:500]
                if not title or not link or link in known:
                    continue
                matched = classify(f"{title} {summary} {link}")
                if not matched:
                    continue
                category, content_type = matched
                added.append({
                    "title": title[:250], "url": link, "summary": summary,
                    "category": category, "content_type": content_type,
                    "source": feed.feed.get("title", feed_url),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "status": "pending",
                })
                known.add(link)
        except Exception as exc:
            errors.append(f"{feed_url}: {type(exc).__name__}: {exc}")
    combined = (old + added)[-2000:]
    PENDING.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Feeds checked: {len(FEEDS)} | New matching posts: {len(added)} | Total saved: {len(combined)}")
    for error in errors:
        print(f"WARNING: {error}")

if __name__ == "__main__":
    main()
