from importlib import metadata

from fastapi import FastAPI

from src.obs_glx.api.router import router as workflows_router

try:
    version = metadata.version("obs-glx")
except metadata.PackageNotFoundError:
    version = "0.1.0"

app = FastAPI(
    title="Obsidian Galaxy API",
    version=version,
    description="Orchestration Graphs for Obsidian Vault.",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(workflows_router, prefix="/api", tags=["workflows"])
app.include_router(workflows_router, prefix="/api/v1", tags=["workflows"])
