from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_router = APIRouter()

# Centralizar os includes aqui mantém `main.py` pequeno e evita acoplamento
# entre a criação da aplicação e a organização das rotas de negócio.
api_router.include_router(health_router, tags=["health"])
