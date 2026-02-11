from fastapi import FastAPI, Query, Request
import os, hashlib, subprocess
from .db import fetch_one, fetch_all
from .audit import get_stuck_orders  # si existe

app = FastAPI(title="Sendmax Backoffice API", version="0.5.2")

def _git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None

@app.get("/version")
def version():
    # fingerprint del archivo main.py para comprobar deploy real
    try:
        with open(__file__, "rb") as f:
            fp = hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        fp = None
    return {
        "ok": True,
        "git_sha": _git_sha(),
        "file_fp": fp,
        "env": os.getenv("ENV", "local"),
        "db_ro_set": bool(os.getenv("DATABASE_URL_RO")),
    }

@app.get("/health")
def health():
    return {"ok": True, "service": "backoffice-api", "version": "0.5.2"}

# --- (resto de tus endpoints actuales deben quedarse como están) ---
