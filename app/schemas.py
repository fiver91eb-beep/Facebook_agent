from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl


class ContentItem(BaseModel):
    title: str
    url: HttpUrl
    source: str
    summary: str = ""
    content_type: Literal["article", "video"] = "article"
    published_at: datetime | None = None
    status: Literal["pending", "approved", "published", "rejected"] = "pending"


class IngestResult(BaseModel):
    feeds_checked: int
    items_found: int
    items_added: int
    errors: list[str] = []
