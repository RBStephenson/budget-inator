"""
Standalone entry point for Budget-inator.

Serves the FastAPI backend + the pre-built Vite frontend in a single process.
The API is mounted under /api to match the frontend's BASE = "/api"; the React
SPA is served from / with an index.html fallback so client-side routes
(/bills, /settings) work on direct navigation or refresh.

The SQLite database lives in the platform-appropriate user data dir so it
survives app updates.
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths and point the app at the user-data DB before importing app code
# ---------------------------------------------------------------------------


def _user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "Budget-inator"


def _frontend_dist() -> Path:
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller bundle
        return Path(sys._MEIPASS) / "dist"  # type: ignore[attr-defined]
    # Running from source: project_root/frontend/dist
    return Path(__file__).parent.parent / "frontend" / "dist"


data_dir = _user_data_dir()
data_dir.mkdir(parents=True, exist_ok=True)

# Point the app at the user-data DB (not the Docker ./data volume). This must
# happen before importing app.config / app.database, which read DATABASE_URL.
os.environ["DATABASE_URL"] = f"sqlite:///{data_dir / 'budget.db'}"

# ---------------------------------------------------------------------------
# Build the combined app
# ---------------------------------------------------------------------------

import app.models  # noqa: E402,F401  (register models on Base.metadata)
from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app as api_app  # noqa: E402

# Create any missing tables in the user-data DB (fresh install / new release).
Base.metadata.create_all(bind=engine)


class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to index.html for unknown paths.

    Lets the React SPA's client-side routes resolve on direct navigation
    instead of 404-ing (the Docker build relies on nginx try_files for this).
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


root = FastAPI(title="Budget-inator")
# API first so /api/* takes precedence over the SPA catch-all.
root.mount("/api", api_app)

dist = _frontend_dist()
if dist.exists():
    root.mount("/", SPAStaticFiles(directory=str(dist), html=True), name="static")
else:

    @root.get("/")
    def _no_frontend():
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

PORT = 8585


def _open_browser():
    time.sleep(2.0)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    import uvicorn

    print(f"Budget-inator running at http://localhost:{PORT}")
    print(f"Data stored in: {data_dir}")
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(root, host="127.0.0.1", port=PORT, log_level="warning")
