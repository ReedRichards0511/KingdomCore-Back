from fastapi import APIRouter

from kingdom.contexts.identity.api.routers.auth import router as auth_router

identity_router = APIRouter()
identity_router.include_router(auth_router)

__all__ = ["identity_router"]
