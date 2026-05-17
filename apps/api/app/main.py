from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


app = FastAPI(title="FitPlate Coach API", version="0.1.0")


@app.get("/api/v0/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="fitplate-api", version="0.1.0")
