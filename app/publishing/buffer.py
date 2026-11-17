import httpx
from config.settings import settings


BUFFER_ENDPOINT = "https://api.buffer.com"


class BufferPublishingError(RuntimeError):
    pass


def _request(query: str, variables: dict | None = None) -> dict:
    if not settings.buffer_api_key:
        raise BufferPublishingError("Buffer API key is not configured.")
    try:
        response = httpx.post(
            BUFFER_ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.buffer_api_key}",
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise BufferPublishingError(f"Buffer API request failed: {exc}") from exc
    except ValueError as exc:
        raise BufferPublishingError("Buffer returned an invalid JSON response.") from exc

    if payload.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in payload["errors"]
        )
        raise BufferPublishingError(messages)
    return payload.get("data") or {}


def list_channels() -> list[dict]:
    """Return connected Buffer channels, grouped across the account's organizations."""
    organizations_query = """
    query GetOrganizations {
      account {
        organizations {
          id
          name
        }
      }
    }
    """
    data = _request(organizations_query)
    organizations = (data.get("account") or {}).get("organizations") or []
    results: list[dict] = []

    channels_query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id
        name
        service
        descriptor
        externalLink
        isDisconnected
      }
    }
    """
    for organization in organizations:
        org_id = organization.get("id")
        if not org_id:
            continue
        channel_data = _request(channels_query, {"organizationId": org_id})
        for channel in channel_data.get("channels") or []:
            results.append({
                **channel,
                "organization_id": org_id,
                "organization_name": organization.get("name", ""),
            })
    return results


def publish_link(message: str, link: str, title: str = "", description: str = "") -> dict:
    """Add an approved link post to the configured Buffer channel queue."""
    if not settings.publish_enabled:
        raise BufferPublishingError("Publishing is disabled. Enable it only after Buffer is configured.")
    if not settings.buffer_api_key or not settings.buffer_channel_id:
        raise BufferPublishingError("Configure BUFFER_API_KEY and BUFFER_CHANNEL_ID first.")

    mutation = """
    mutation QueueSportsPost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            text
            dueAt
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    input_data = {
        "text": message,
        "channelId": settings.buffer_channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
        "assets": [],
        "metadata": {
            "facebook": {
                "type": "post",
                "linkAttachment": {
                    "url": link,
                    "title": title or message[:100],
                    "description": description or None,
                },
            }
        },
    }
    data = _request(mutation, {"input": input_data})
    result = data.get("createPost") or {}
    if result.get("message"):
        raise BufferPublishingError(result["message"])
    post = result.get("post")
    if not post:
        raise BufferPublishingError("Buffer did not confirm that the post was added to its queue.")
    return post
