from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

# Cada domínio da aplicação terá seu próprio router nas próximas etapas.
# Centralizar os includes aqui mantém `main.py` pequeno e evita acoplamento
# entre a criação da aplicação e a organização das rotas de negócio.
api_router.include_router(health.router)
