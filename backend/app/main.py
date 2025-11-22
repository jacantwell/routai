from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config import settings

app = FastAPI(
)

# Set all CORS enabled origins
if settings.CORS_ORGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/ping")
def ping():
    return "pong"