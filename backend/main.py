import asyncio
import time
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import TEMP_DIR, SESSION_TTL, CLEANUP_INTERVAL
from routes import upload, merge, thumbnails
from services import session_store


async def cleanup_loop():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        now = time.time()
        for session_dir in TEMP_DIR.iterdir():
            meta = session_store.load_meta(session_dir)
            if meta and (now - meta["created_at"]) > SESSION_TTL:
                shutil.rmtree(session_dir, ignore_errors=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="PDF Merger", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(merge.router)
app.include_router(thumbnails.router)


@app.get("/health")
def health():
    return {"status": "ok"}
