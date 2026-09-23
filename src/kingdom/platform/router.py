from __future__ import annotations

from fastapi import APIRouter

from kingdom.contexts.identity.api.routers import identity_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(identity_router)
