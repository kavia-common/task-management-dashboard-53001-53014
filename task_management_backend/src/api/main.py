from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.api.db.init_db import init_db
from src.api.db.session import engine
from src.api.realtime.manager import manager
from src.api.routes.auth import router as auth_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.users import router as users_router

openapi_tags = [
    {"name": "health", "description": "Service health endpoints"},
    {"name": "auth", "description": "Authentication endpoints (JWT)"},
    {"name": "users", "description": "User management endpoints"},
    {"name": "tasks", "description": "Task CRUD endpoints with filtering/sorting"},
    {"name": "realtime", "description": "WebSocket endpoints for real-time task updates"},
]

app = FastAPI(
    title="Task Management Backend API",
    description=(
        "Backend for the Task Management Dashboard.\n\n"
        "Authentication is performed via JWT Bearer tokens obtained from `/auth/login`.\n\n"
        "Real-time updates are available via WebSocket:\n"
        "- Connect to `/ws/tasks` (no auth enforced in this template)\n"
        "- You will receive `task_event` messages whenever tasks are created/updated/deleted.\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize DB schema on startup."""
    await init_db(engine)


@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Basic service health check.",
    operation_id="health_check",
)
def health_check():
    return {"message": "Healthy"}


@app.get(
    "/docs/ws",
    tags=["realtime"],
    summary="WebSocket usage help",
    description="Human-readable notes on connecting to the WebSocket endpoint for task events.",
    operation_id="websocket_usage_help",
)
def websocket_usage_help():
    return {
        "endpoint": "/ws/tasks",
        "message_format": {
            "type": "task_event",
            "event": "created|updated|deleted",
            "task": {"id": "...", "title": "..."},
            "ts": "ISO8601 UTC timestamp",
        },
        "notes": [
            "This template does not enforce auth on WebSocket connections.",
            "Clients should reconnect on disconnect and handle duplicate events.",
        ],
    }


@app.websocket("/ws/tasks")
async def ws_tasks(websocket: WebSocket):
    """WebSocket endpoint broadcasting task change events.

    Client usage:
    - Open a WebSocket connection to `/ws/tasks`
    - Listen for JSON text messages of the form:
      { "type": "task_event", "event": "created|updated|deleted", "task": {...}, "ts": "..." }
    """
    await manager.connect(websocket)
    try:
        # Keep connection open; we don't require client messages, but we read to detect disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
        raise
