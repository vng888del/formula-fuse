import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import atoms, formulas

app = FastAPI(
    title="Atom Intelligence Engine",
    description="Formula Fuse Studio Backend API",
    version="0.1.0",
)

_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["http://localhost:3000", "http://localhost:3001"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(atoms.router)
app.include_router(formulas.router)


@app.get("/")
async def root():
    return {"name": "Atom Intelligence Engine", "version": "0.1.0", "status": "ok"}


@app.get("/health")
async def health():
    from app.db.database import (
        _get_supabase, _get_database_url, _postgres_available, _supabase_available,
        get_all_atoms,
    )

    # DB 接続状態を判定
    db_url = _get_database_url()
    sb_url = os.getenv("SUPABASE_URL", "")

    if _postgres_available is True:
        db_mode = "postgresql"
        db_status = "connected"
    elif _postgres_available is False:
        db_mode = "postgresql"
        db_status = "error"
    elif _supabase_available is True:
        db_mode = "supabase"
        db_status = "connected"
    elif _supabase_available is False:
        db_mode = "supabase" if sb_url else "none"
        db_status = "error" if sb_url else "not_configured"
    elif db_url:
        db_mode = "postgresql"
        db_status = "pending"
    elif sb_url and "your-" not in sb_url:
        db_mode = "supabase"
        db_status = "pending"
    else:
        db_mode = "memory"
        db_status = "in_memory"

    atoms_count = len(get_all_atoms())

    return {
        "status": "ok",
        "version": "0.1.0",
        "db": {
            "mode": db_mode,
            "status": db_status,
            "persistent": db_status == "connected",
        },
        "data": {
            "atoms": atoms_count,
        },
    }
