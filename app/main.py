from fastapi import FastAPI, APIRouter
from routers import health, emails

import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json"
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health.router)
api_v1_router.include_router(emails.router)

app.include_router(api_v1_router)