from app.database import add_item
from app.sources.rss import fetch_feed
from config.settings import settings


def run_ingestion() -> dict:
    feeds = settings.feed_urls()
    found = 0
    added = 0
    errors: list[str] = []
    for feed_url in feeds:
        try:
            items = fetch_feed(feed_url)
            found += len(items)
            for item in items:
                if add_item(item):
                    added += 1
        except Exception as exc:
            errors.append(f'{feed_url}: {type(exc).__name__}: {exc}')
    return {'feeds_checked': len(feeds), 'items_found': found, 'items_added': added, 'errors': errors}
