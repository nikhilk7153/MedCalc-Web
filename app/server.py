from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import BASE_DIR
from app.routes import calculators

app = FastAPI(title="MedCalc API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    calculators.router,
    prefix="/api/calculators",
    tags=["calculators"],
)

app.mount(
    "/",
    StaticFiles(directory=str(BASE_DIR), html=True),
    name="static",
)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

