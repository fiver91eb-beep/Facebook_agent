from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import httpx

from app import database
from app.agents.runner import run_ingestion
from app.database import get_item, list_items, set_status
from app.publishing.facebook import PublishingDisabledError, publish_link
from config.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_db()
    yield


app = FastAPI(title=settings.app_name,
              description='Collect sports articles and video links, then review before publishing.',
              version='0.1.0', lifespan=lifespan)


@app.get('/')
def root():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')


@app.get('/api/status')
def api_status():
    return {'name': settings.app_name, 'status': 'running', 'docs': '/docs',
            'publishing_enabled': settings.publish_enabled}


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/api/ingest')
def ingest():
    try:
        return run_ingestion()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get('/api/items')
def items(status: str | None = Query(default=None, pattern='^(pending|approved|published|rejected)$'),
          limit: int = Query(default=50, ge=1, le=200)):
    return list_items(status=status, limit=limit)


@app.post('/api/items/{item_id}/approve')
def approve(item_id: int):
    if not get_item(item_id):
        raise HTTPException(status_code=404, detail='Content item not found')
    set_status(item_id, 'approved')
    return {'id': item_id, 'status': 'approved'}


@app.post('/api/items/{item_id}/reject')
def reject(item_id: int):
    if not get_item(item_id):
        raise HTTPException(status_code=404, detail='Content item not found')
    set_status(item_id, 'rejected')
    return {'id': item_id, 'status': 'rejected'}


@app.post('/api/items/{item_id}/publish')
def publish(item_id: int):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail='Content item not found')
    if item['status'] != 'approved':
        raise HTTPException(status_code=409, detail='Approve this item before publishing')
    try:
        result = publish_link(item['title'], item['url'])
    except PublishingDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f'Facebook API request failed: {exc}') from exc
    set_status(item_id, 'published')
    return {'id': item_id, 'status': 'published', 'facebook': result}
