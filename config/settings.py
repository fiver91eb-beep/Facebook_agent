from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sports Lover Agent"
    database_path: str = "data/sports_agent.db"
    request_timeout_seconds: int = 15
    max_items_per_feed: int = 30
    sports_feeds: str = "[]"
    publish_enabled: bool = False
    buffer_api_key: str = ""
    buffer_channel_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def feed_urls(self) -> list[str]:
        import json
        try:
            value = json.loads(self.sports_feeds)
        except json.JSONDecodeError as exc:
            raise ValueError("SPORTS_FEEDS must be a JSON array of URLs") from exc
        if not isinstance(value, list) or not all(isinstance(item, str) and item.startswith(("https://", "http://")) for item in value):
            raise ValueError("SPORTS_FEEDS must contain only HTTP(S) URLs")
        return value


settings = Settings()
