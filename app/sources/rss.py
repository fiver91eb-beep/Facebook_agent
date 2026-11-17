from datetime import timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.processing.filters import classify_content, looks_sports_related
from config.settings import settings


def _published(entry: dict) -> str | None:
    raw = entry.get('published') or entry.get('updated')
    if not raw:
        return None
    try:
        value = parsedate_to_datetime(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def fetch_feed(url: str) -> list[dict]:
    response = httpx.get(url, timeout=settings.request_timeout_seconds, follow_redirects=True,
                         headers={'User-Agent': 'SportsLoverAgent/0.1 RSS reader'})
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    results = []
    for entry in parsed.entries[:settings.max_items_per_feed]:
        title = str(entry.get('title', '')).strip()
        link = str(entry.get('link', '')).strip()
        summary = str(entry.get('summary', '')).strip()
        if not title or not link or not link.startswith(('https://', 'http://')):
            continue
        if not looks_sports_related(title, summary):
            continue
        results.append({
            'title': title[:500], 'url': link,
            'source': str(parsed.feed.get('title', url))[:200],
            'summary': summary[:4000],
            'content_type': classify_content(entry),
            'published_at': _published(entry),
        })
    return results
