"""
FastAPI application entry point.
Lifespan: run Alembic migrations, init AGE graph schema, init Qdrant collection,
create default Admin user if none exists.
"""
from __future__ import annotations

import logging
import os
import secrets
import string

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings

settings = get_settings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def _lifespan(app: FastAPI):
    # Run Alembic migrations
    _run_migrations()

    # Init AGE graph schema (vertex/edge labels)
    from database import AsyncSessionLocal, init_db
    await init_db()
    async with AsyncSessionLocal() as db:
        from retrieval.graph_store import init_graph_schema
        await init_graph_schema(db)

    # Init Qdrant collection
    from retrieval.vector_store import ensure_collection
    await ensure_collection()

    # Create default admin user if no users exist
    await _ensure_admin_user()

    log.info("Company Brain startup complete")
    yield
    log.info("Company Brain shutting down")


def _run_migrations() -> None:
    import subprocess
    try:
        # Invoke the `alembic` console script directly rather than `python -m alembic`:
        # `-m` prepends the cwd to sys.path, which would let our own ./alembic
        # migrations directory shadow the real installed `alembic` package.
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        if result.returncode != 0:
            log.warning(f"Alembic migration warning: {result.stderr}")
        else:
            log.info("Database migrations applied")
    except Exception as exc:
        log.warning(f"Could not run migrations: {exc}")


async def _ensure_admin_user() -> None:
    from sqlalchemy import select
    from database import AsyncSessionLocal
    from access_control.models import User, RoleEnum
    from passlib.context import CryptContext

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.role == RoleEnum.admin))
        if result.scalar_one_or_none():
            return

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        one_time_password = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
        )
        admin = User(
            email="admin@company-brain.local",
            username="admin",
            hashed_password=pwd_context.hash(one_time_password),
            role=RoleEnum.admin,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"\n{'='*60}")
        print(f"  ADMIN USER CREATED")
        print(f"  Email:    admin@company-brain.local")
        print(f"  Password: {one_time_password}")
        print(f"  Change this password immediately after first login.")
        print(f"{'='*60}\n")


app = FastAPI(
    title="Company Brain",
    description="AI-native institutional memory platform",
    version="1.0.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from api.analytics import router as analytics_router
from api.auth import router as auth_router
from api.documents import router as documents_router
from api.query import router as query_router
from api.users import router as users_router
from mcp_server import router as mcp_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(analytics_router)
app.include_router(mcp_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}
