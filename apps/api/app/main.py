from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.formparsers import MultiPartParser

from app.routers.food import router as food_router


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


# Keep Starlette's multipart spool threshold above the 10 MB app upload cap so
# accepted image uploads remain in memory at the framework parser layer.
MultiPartParser.spool_max_size = 11 * 1024 * 1024

app = FastAPI(title="FitPlate Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(food_router)


@app.get("/api/v0/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="fitplate-api", version="0.1.0")
