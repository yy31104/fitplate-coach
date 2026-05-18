from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers.food import router as food_router


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


app = FastAPI(title="FitPlate Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(food_router)


@app.get("/api/v0/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="fitplate-api", version="0.1.0")
