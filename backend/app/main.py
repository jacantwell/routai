import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.routes.chats import router as chat_router
from app.api.routes.sessions import router as session_router
from app.config.logging import setup_logging
from app.api.services.session_manager import SessionManager

from app.config import settings, setup_logging

# Setup logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up Bikepacking Route Planner API")
    logger.info("Session manager initialized")

    # Global session manager instance
    app.state.session_manager = SessionManager()
    
    yield
    
    # Shutdown
    logger.info("Shutting down API")

app = FastAPI(lifespan=lifespan
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


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/ping")
def ping():
    return "pong"

# Include routers
app.include_router(chat_router, tags=["chats"])
app.include_router(session_router, tags=["sessions"])

