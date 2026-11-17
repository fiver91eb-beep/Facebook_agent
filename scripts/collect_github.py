import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PENDING = DATA / "pending_posts.json"
FEEDS = [
    "https://feeds.bbci.co.uk/sport/rss.xml",
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
]
MAX_PER_FEED = 40
MAX_AGE_HOURS = 72
RETIREMENT_TERMS = (
    "retire", "retirement", "retires", "retired", "farewell",
    "steps down", "quits international", "leaves international cricket",
)
EXCLUDE_TERMS = (
    "american football", "nfl", "rugby", "formula 1", "formula one",
    "f1", "tennis", "basketball", "boxing", "darts", "golf", "hockey",
)
CRICKET_TERMS = (
    "cricket", "ipl", "psl", "test match", "odi", "t20", "world cup",
    "wicket", "wickets", "batsman", "batter", "bowler", "innings",
    "run chase", "six", "boundary", "century", "hat-trick", "super over",
)
FOOTBALL_TERMS = (
    "football", "soccer", "premier league", "champions league", "fifa",
    "uefa", "goal", "goals", "striker", "penalty", "free-kick",
    "kick-off", "derby", "world cup", "fa cup", "la liga", "serie a",
)
TREND_TERMS = (
    "hat-trick", "hat trick", "century", "double century", "super over",
    "last-minute", "last minute", "wonder goal", "stunning goal",
    "comeback", "upset", "record", "fastest", "final", "derby",
    "penalty shootout", "penalty save", "bicycle kick", "screamer",
    "six sixes", "six-hitting", "thriller", "dramatic win", "dramatic finish",
    "viral", "best goals", "best saves", "highlights", "top moments",
)

def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()

def published_time(entry):
    raw = entry.get("published_parsed") or entry.get("updated_parsed")
    if raw:
        return datetime(*raw[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def classify(text, feed_url):
    value = text.lower()
    if any(term in value for term in EXCLUDE_TERMS):
        return None
    if "cricket" in feed_url.lower() or "espncricinfo" in feed_url.lower():
        return "cricket"
    if "/football/" in feed_url.lower():
        return "football"
    if any(term in value for term in CRICKET_TERMS):
        return "cricket"
    if any(term in value for term in FOOTBALL_TERMS):
        return "football"
    return None

def trend_score(title, summary, link, published):
    value = f"{title} {summary}".lower()
    score = 0.0
    if "/videos/" in link.lower() or ".mp4" in link.lower() or "youtube.com" in link.lower():
        score += 3.0
    score += min(6.0, sum(1.5 for term in TREND_TERMS if term in value))
    age_hours = max(0.0, (datetime.now(timezone.utc) - published).total_seconds() / 3600)
    score += max(0.0, 2.0 - age_hours / 36.0)
    return round(score, 2)

def main():
    DATA.mkdir(exist_ok=True)
    old = json.loads(PENDING.read_text(encoding="utf-8")) if PENDING.exists() else []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    known = set()
    retained = []
    for item in old:
        try:
            dt = datetime.fromisoformat(item.get("published_at", item.get("collected_at", "")))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if (item.get("category") in ("cricket", "football")
                and dt >= cutoff
                and not any(term in (item.get("title", "") + " " + item.get("summary", "")).lower()
                            for term in RETIREMENT_TERMS)):
            retained.append(item)
            known.add(item.get("url"))

    added = []
    errors = []
    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if getattr(feed, "bozo", False) and not feed.entries:
                errors.append(f"Feed parse failed: {feed_url}")
                continue
            for entry in feed.entries[:MAX_PER_FEED]:
                title = clean(entry.get("title"))
                link = (entry.get("link") or "").strip()
                summary = clean(entry.get("summary"))[:700]
                if not title or not link or link in known:
                    continue
                published = published_time(entry)
                if published < cutoff or published > now + timedelta(hours=2):
                    continue
                combined = f"{title} {summary}"
                if any(term in combined.lower() for term in RETIREMENT_TERMS):
                    continue
                category = classify(combined, feed_url)
                if category not in ("cricket", "football"):
                    continue
                score = trend_score(title, summary, link, published)
                if score < 1.5:
                    continue
                added.append({
                    "title": title[:250],
                    "url": link,
                    "summary": summary,
                    "category": category,
                    "content_type": "video" if "/videos/" in link.lower() or ".mp4" in link.lower() else "story",
                    "source": feed.feed.get("title", feed_url),
                    "published_at": published.isoformat(),
                    "collected_at": now.isoformat(),
                    "trend_score": score,
                    "status": "pending",
                })
                known.add(link)
        except Exception as exc:
            errors.append(f"{feed_url}: {type(exc).__name__}: {exc}")

    combined = retained + added
    combined.sort(key=lambda item: (float(item.get("trend_score", 0)), item.get("published_at", "")), reverse=True)
    combined = combined[:500]
    PENDING.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Cricket/football feeds checked: {len(FEEDS)} | New trend-filtered stories: {len(added)} | Pending pool: {len(combined)}")
    print("Filters: cricket and association football only; last 72 hours; retirement-only stories excluded.")
    for error in errors:
        print(f"WARNING: {error}")

if __name__ == "__main__":
    main()
