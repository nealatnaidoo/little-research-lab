import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.deps import get_settings
from src.app_shell.config import validate_ops_rules
from src.rules.loader import load_rules


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    # Load rules and validate on startup (fail-fast)
    try:
        rules = load_rules(settings.rules_path)
        validate_ops_rules(rules, settings.base_dir)
        print(f"INFO: Rules loaded from {settings.rules_path}")
    except Exception as e:
        print(f"CRITICAL: Rules load failed: {e}", file=sys.stderr)
        sys.exit(1)

    yield
    # Shutdown cleanup if needed


app = FastAPI(
    title="Little Research Lab API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Routers ---
from src.api.routes import assets, auth, content, public, users  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(content.router, prefix="/api/content", tags=["Content"])
app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(public.router, prefix="/api/public", tags=["Public"])


# CORS (Allow Frontend)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "ok", "service": "api"}
