"""Router: Diagnósticos y Health checks"""

import os
from fastapi import APIRouter, Depends
from ..db import fetch_one
from ..auth import verify_api_key

router = APIRouter(tags=["diagnostics"])


@router.get("/health")
def health():
    return {"ok": True, "service": "backoffice-api", "version": "0.6.0"}


@router.get("/diag/env")
def diag_env(api_key: str = Depends(verify_api_key)):
    return {
        "ok": True,
        "has_DATABASE_URL_RO": bool(os.getenv("DATABASE_URL_RO")),
        "has_DATABASE_URL_RW": bool(os.getenv("DATABASE_URL_RW")),
        "has_BACKOFFICE_API_KEY": bool(os.getenv("BACKOFFICE_API_KEY")),
    }


@router.get("/diag/db-users")
def diag_db_users(api_key: str = Depends(verify_api_key)):
    ro = fetch_one("SELECT current_user AS u", ())
    rw = fetch_one("SELECT current_user AS u", (), rw=True)
    return {"ok": True, "ro_user": ro["u"] if ro else None, "rw_user": rw["u"] if rw else None}


@router.get("/diag/db-roles")
def diag_db_roles(api_key: str = Depends(verify_api_key)):
    ro = fetch_one("SELECT current_user AS u", (), rw=False)
    rw = fetch_one("SELECT current_user AS u", (), rw=True)
    return {"ro_user": ro["u"] if ro else None, "rw_user": rw["u"] if rw else None}


@router.get("/version2")
def version2():
    return {"ok": True, "marker": "refactored_routers", "ts": "2026-02-11"}


@router.get("/gitsha")
def gitsha():
    return {
        "ok": True,
        "railway_commit": os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("RAILWAY_GIT_COMMIT") or "unknown",
    }
