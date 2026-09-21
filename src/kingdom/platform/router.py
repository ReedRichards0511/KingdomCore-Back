"""Router raiz de la API.

Cada contexto expone su propio router; aqui se montan todos bajo ``/api/v1``.
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

# Conforme cada contexto tenga endpoints, se montan aqui:
#
#   from kingdom.contexts.identity.api.routers import identity_router
#   api_router.include_router(identity_router)
