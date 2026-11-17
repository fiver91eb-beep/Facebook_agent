import httpx
from config.settings import settings


class PublishingDisabledError(RuntimeError):
    pass


def publish_link(message: str, link: str) -> dict:
    """Publish an approved link post; disabled unless explicitly configured."""
    if not settings.publish_enabled:
        raise PublishingDisabledError('Facebook publishing is disabled. Configure and verify Page permissions before enabling it.')
    if not settings.facebook_page_id or not settings.facebook_page_access_token:
        raise PublishingDisabledError('Facebook Page ID/token is not configured.')
    endpoint = f'https://graph.facebook.com/{settings.meta_graph_api_version}/{settings.facebook_page_id}/feed'
    response = httpx.post(endpoint, data={
        'message': message, 'link': link, 'access_token': settings.facebook_page_access_token,
    }, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    return response.json()
