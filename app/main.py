from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.store import WebhookStore

APP_TITLE = "GitLab Hook Live Dashboard"
APP_VERSION = "1.0.0"

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
MAX_EVENTS = int(os.getenv("MAX_EVENTS", "1000"))

app = FastAPI(title=APP_TITLE, version=APP_VERSION)
store = WebhookStore(max_events=MAX_EVENTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


def parse_event(request_body: dict[str, Any], gitlab_event_header: str | None, source_ip: str) -> dict[str, Any]:
    project_name = (
        request_body.get("project", {}).get("path_with_namespace")
        or request_body.get("project", {}).get("name")
        or request_body.get("repository", {}).get("name")
        or "unknown-project"
    )

    author = (
        request_body.get("user_username")
        or request_body.get("user_name")
        or request_body.get("user", {}).get("username")
        or "unknown-user"
    )

    object_kind = request_body.get("object_kind")
    event_type = object_kind or gitlab_event_header or "unknown-event"

    source = request_body.get("project", {}).get("web_url") or source_ip

    return {
        "received_at": datetime.now(tz=timezone.utc).isoformat(),
        "event_type": str(event_type),
        "project": str(project_name),
        "author": str(author),
        "source": str(source),
        "summary": str(request_body.get("event_name") or object_kind or gitlab_event_header or "webhook"),
        "payload": request_body,
    }


@app.get("/")
async def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
async def health() -> JSONResponse:
    snapshot = await store.snapshot()
    return JSONResponse({"status": "ok", "events": snapshot["stats"]["total_events"]})


@app.get("/api/logs")
async def get_logs() -> JSONResponse:
    return JSONResponse(await store.snapshot())


@app.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: str | None = Header(default=None),
    x_gitlab_token: str | None = Header(default=None),
) -> JSONResponse:
    if WEBHOOK_SECRET and x_gitlab_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payload = await request.json()
    source_ip = request.client.host if request.client else "unknown"
    event = parse_event(payload, x_gitlab_event, source_ip)
    stats = await store.add_event(event)

    return JSONResponse({"ok": True, "event_type": event["event_type"], "stats": stats})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await store.register(websocket)

    # Send initial state right after connection so dashboard hydrates instantly.
    await websocket.send_json({"type": "snapshot", **(await store.snapshot())})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await store.unregister(websocket)
