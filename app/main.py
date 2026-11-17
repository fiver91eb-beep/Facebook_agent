import asyncio
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from app import database
from app.agents.runner import run_ingestion
from app.database import get_item, list_items, set_status
from app.publishing.buffer import BufferPublishingError, list_channels, publish_link
from config.settings import settings


async def automatic_ingestion_loop():
    """Collect configured feeds periodically without blocking the web server."""
    while True:
        await asyncio.sleep(settings.ingest_interval_seconds)
        if not settings.auto_ingest_enabled:
            continue
        try:
            if settings.feed_urls():
                await asyncio.to_thread(run_ingestion)
        except Exception:
            # Keep the scheduler alive; errors are visible through manual collection
            # and server logs, without crashing the web service.
            continue


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    task = asyncio.create_task(automatic_ingestion_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    description="Collect sports articles and video links, review them, and queue approved links through Buffer.",
    version="0.3.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def require_admin_login(request: Request, call_next):
    # Render uses this unauthenticated endpoint for its health check.
    if request.url.path == "/health":
        return await call_next(request)

    username = settings.admin_username
    password = settings.admin_password
    if not username or not password:
        return JSONResponse(
            status_code=503,
            content={"detail": "Admin login is not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD."},
        )

    authorization = request.headers.get("authorization", "")
    try:
        scheme, encoded = authorization.split(" ", 1)
        if scheme.lower() != "basic":
            raise ValueError("Unsupported authentication scheme")
        import base64
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        supplied_username, supplied_password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        supplied_username, supplied_password = "", ""

    valid_user = secrets.compare_digest(supplied_username, username)
    valid_password = secrets.compare_digest(supplied_password, password)
    if not (valid_user and valid_password):
        return JSONResponse(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Sports Lover Agent", charset="UTF-8"'},
            content={"detail": "Admin login required."},
        )
    return await call_next(request)


@app.get("/")
def root():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/status")
def api_status():
    feeds = settings.feed_urls()
    buffer_configured = bool(settings.buffer_api_key and settings.buffer_channel_id)
    return {
        "name": settings.app_name,
        "status": "running",
        "version": app.version,
        "docs": "/docs",
        "admin_login_configured": bool(settings.admin_username and settings.admin_password),
        "auto_ingest_enabled": settings.auto_ingest_enabled,
        "ingest_interval_seconds": settings.ingest_interval_seconds,
        "configured_feed_count": len(feeds),
        "publishing_enabled": settings.publish_enabled and buffer_configured,
        "publisher": "Buffer",
        "buffer_configured": buffer_configured,
        "video_mode": "link_only",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/buffer/channels")
def buffer_channels():
    try:
        return list_channels()
    except BufferPublishingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/ingest")
def ingest():
    try:
        return run_ingestion()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/items")
def items(
    status: str | None = Query(default=None, pattern="^(pending|approved|queued|published|rejected)$"),
    limit: int = Query(default=50, ge=1, le=200),
):
    return list_items(status=status, limit=limit)


@app.post("/api/items/{item_id}/approve")
def approve(item_id: int):
    if not get_item(item_id):
        raise HTTPException(status_code=404, detail="Content item not found")
    set_status(item_id, "approved")
    return {"id": item_id, "status": "approved"}


@app.post("/api/items/{item_id}/reject")
def reject(item_id: int):
    if not get_item(item_id):
        raise HTTPException(status_code=404, detail="Content item not found")
    set_status(item_id, "rejected")
    return {"id": item_id, "status": "rejected"}


@app.post("/api/items/{item_id}/publish")
def publish(item_id: int):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")
    if item["status"] != "approved":
        raise HTTPException(status_code=409, detail="Approve this item before publishing")
    try:
        result = publish_link(
            message=item["title"],
            link=item["url"],
            title=item["title"],
            description=item.get("summary", ""),
        )
    except BufferPublishingError as exc:
        raise HTTPException(status_code=502, detail=f"Buffer publishing failed: {exc}") from exc
    set_status(item_id, "queued")
    return {"id": item_id, "status": "queued", "buffer": result}
