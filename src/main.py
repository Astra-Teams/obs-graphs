from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.v1.routers.workflows import router as workflows_router
from src.container import get_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup: Initialize application dependencies
    app.state.container = get_container()
    yield
    # Shutdown: Add cleanup logic here if needed


app = FastAPI(
    title="FastAPI Template",
    version="0.1.0",
    description="A FastAPI template project",
    lifespan=lifespan,
)

# Include routers
app.include_router(workflows_router, prefix="/api/v1", tags=["workflows"])


@app.get("/")
async def hello_world():
    """
    Hello World endpoint.
    """
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
