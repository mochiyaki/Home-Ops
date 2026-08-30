import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import CallCapExceeded, DangerBlocked, VendorError, VendorNotConfigured
from app.db import init_db
from app.routers import calls, live, tools, voice, house

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

logger = logging.getLogger("homeops")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The Guava SDK reads its key from the environment when it builds a client.
    # Set it once here rather than mutating os.environ on every call.
    settings = get_settings()
    if settings.guava_api_key:
        os.environ["GUAVA_API_KEY"] = settings.guava_api_key
    # Create tables if they are missing. Cheap and idempotent; keeps a fresh
    # `docker compose up` working with no migration step.
    try:
        await init_db()
        logger.info("database ready")
    except Exception:
        logger.exception("database unavailable - start it with: docker compose up -d")
        raise
    yield


app = FastAPI(title="HomeOps", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # Same-origin in production (FastAPI serves frontend/dist). The private
    # ranges are here so a phone or a second laptop on the LAN can hit the API
    # directly, e.g. the Vite dev server on another machine.
    allow_origin_regex=(
        r"https://.*\.onrender\.com"
        r"|http://(localhost|127\.0\.0\.1):\d+"
        r"|http://192\.168\.\d{1,3}\.\d{1,3}:\d+"
        r"|http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+"
        r"|http://172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}:\d+"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(live.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(house.router, prefix="/api")


@app.api_route("/health", methods=["GET", "HEAD"])
def health(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    settings = get_settings()
    from app.services import guava_caller

    # `configured` means credentials exist; `calls_live` means a call placed
    # right now would actually ring a phone. They differ whenever
    # HOMEOPS_ALLOW_REAL_CALLS is off, and the UI needs to know which is which.
    configured = guava_caller.is_ready(settings)
    calls_live = guava_caller.will_dial(settings)
    return {
        "ok": True,
        "mock": not calls_live,
        "configured": configured,
        "calls_live": calls_live,
        "suppression_reason": None if calls_live
        else guava_caller.suppression_reason(settings),
        "dev_shop_phone": bool(settings.homeops_dev_shop_phone),
    }


@app.exception_handler(VendorNotConfigured)
async def not_configured(_request: Request, exc: VendorNotConfigured) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "VendorNotConfigured",
            "vendor": exc.vendor,
            "missing": exc.env_var,
            "detail": str(exc),
        },
    )


@app.exception_handler(VendorError)
async def vendor_error(_request: Request, exc: VendorError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "error": "VendorError",
            "vendor": exc.vendor,
            "detail": exc.detail,
        },
    )


@app.exception_handler(DangerBlocked)
async def danger_blocked(_request: Request, exc: DangerBlocked) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "DangerBlocked", "detail": exc.detail},
    )


@app.exception_handler(CallCapExceeded)
async def call_cap(_request: Request, exc: CallCapExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "CallCapExceeded", "detail": exc.detail},
    )


if DIST.is_dir():
    assets = DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="ui-assets")


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
def spa_index(request: Request, full_path: str = ""):
    # An unmatched /api/ path is a client bug, not a deep link. Returning the
    # SPA here hands the caller a page of HTML where they expect JSON.
    if full_path.startswith("api/"):
        return JSONResponse(
            {"error": "NotFound", "detail": f"No such endpoint: /{full_path}"},
            status_code=404,
        )
    if request.method == "HEAD":
        return Response(status_code=200)
    if full_path:
        candidate = (DIST / full_path).resolve()
        if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
            return FileResponse(candidate)
    index = DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"error": "UI build missing"}, status_code=503)


def run() -> None:
    import os

    import uvicorn

    settings = get_settings()
    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
