from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.database import Base, engine
from app.routers import auth_router, tasks, rooms, stats, chat
from app.services.seed import sync_from_yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Version wechselt mit jedem Container-Start -> Frontend kann Drift erkennen
APP_VERSION = str(int(time.time()))


def _migrate_schema():
    insp = inspect(engine)
    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        if "oidc_sub" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN oidc_sub VARCHAR(255)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_oidc_sub ON users(oidc_sub)"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
    sync_from_yaml()
    yield


app = FastAPI(title="Putzplan", lifespan=lifespan)


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response: Response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-store, must-revalidate"
    elif path.startswith("/static/"):
        # statische Assets: revalidate, aber nicht hart cachen
        response.headers["Cache-Control"] = "no-cache"
    elif path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-App-Version"] = APP_VERSION
    return response


@app.get("/api/version")
def version():
    return {"version": APP_VERSION}


app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
