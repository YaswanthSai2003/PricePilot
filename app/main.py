from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.database import create_db_and_tables

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="Revenue Intelligence API for Short-Term Rental Analytics",
)

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if settings.debug else allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return{
        "app":"PricePilot",
        "description":"Revenue Intelligence API for Short term Rental Analytics",
        "docs_url":"/docs",
        "openapi_url":"/openapi.json",
        "health_check":"/api/health",
        "version":"1.0.0"
    }
