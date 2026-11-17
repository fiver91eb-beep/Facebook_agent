import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PENDING = DATA / "pending_posts.json"
PUBLISHED = DATA / "published_urls.json"
ENDPOINT = "https://api.buffer.com"
MAX_PER_RUN = 3

def buffer_request(query, variables, api_key):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Buffer request failed: {exc}") from exc
    if result.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "GraphQL error") for e in result["errors"]))
    return result.get("data") or {}

def main():
    api_key = os.getenv("BUFFER_API_KEY", "").strip()
    channel_id = os.getenv("BUFFER_CHANNEL_ID", "").strip()
    if not api_key or not channel_id:
        raise SystemExit("Missing BUFFER_API_KEY or BUFFER_CHANNEL_ID GitHub Actions secret.")

    posts = json.loads(PENDING.read_text(encoding="utf-8")) if PENDING.exists() else []
    published = set(json.loads(PUBLISHED.read_text(encoding="utf-8"))) if PUBLISHED.exists() else []
    # Only take the newest three not-yet-queued links. Older backlog is left untouched.
    candidates = []
    for item in reversed(posts):
        url = item.get("url")
        if url and url not in published:
            candidates.append(item)
        if len(candidates) >= MAX_PER_RUN:
            break

    mutation = """
    mutation QueueSportsPost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text dueAt } }
        ... on MutationError { message }
      }
    }
    """
    count = 0
    for item in candidates:
        url = item["url"]
        data = buffer_request(mutation, {"input": {
            "text": item.get("title", "Sports update"),
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [],
            "metadata": {"facebook": {"type": "post", "linkAttachment": {
                "url": url,
                "title": item.get("title", "")[:100],
                "description": item.get("summary", "") or None,
            }}},
        }}, api_key)
        result = data.get("createPost") or {}
        if result.get("message") or not result.get("post"):
            raise RuntimeError(result.get("message") or f"Buffer did not confirm queueing: {url}")
        published.add(url)
        PUBLISHED.write_text(json.dumps(sorted(published), indent=2) + "\n", encoding="utf-8")
        count += 1
        print(f"Queued in Buffer: {item.get('title', url)} (post ID: {result['post'].get('id')})")
    print(f"New links added to Buffer queue: {count}")

if __name__ == "__main__":
    main()
