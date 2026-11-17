from urllib.parse import urlparse

VIDEO_SUFFIXES = (".mp4", ".mov", ".m3u8", ".webm")
VIDEO_HOST_PATTERNS = ("youtube.com/watch", "youtube.com/shorts/", "youtu.be/", "vimeo.com/")
SPORTS_TERMS = (
    "sport", "football", "soccer", "cricket", "tennis", "basketball",
    "baseball", "hockey", "formula 1", "formula one", "f1", "olympic",
    "match", "league", "championship", "goal", "wicket", "player", "team",
    "rugby", "golf", "boxing", "mma", "ufc", "badminton", "volleyball",
    "athletics", "marathon", "cycling", "motorsport", "racing", "grand prix",
    "premier league", "champions league", "world cup", "wimbledon",
    "super bowl", "nba", "nfl", "mlb", "nhl",
)


def classify_content(entry: dict) -> str:
    media = entry.get("media_content") or []
    enclosures = entry.get("enclosures") or []
    links = entry.get("links") or []
    candidates = [str(item.get("url", "")) for item in media + enclosures + links]
    candidates.append(str(entry.get("link", "")))
    if any(
        urlparse(url).path.lower().endswith(VIDEO_SUFFIXES)
        or any(host in url.lower() for host in VIDEO_HOST_PATTERNS)
        or "video" in url.lower()
        for url in candidates
    ):
        return "video"
    return "article"


def looks_sports_related(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(term in text for term in SPORTS_TERMS)
