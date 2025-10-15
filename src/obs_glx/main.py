from fastapi import FastAPI
from src.obs_graphs.api.router import router as workflows_router

app = FastAPI(
    title="FastAPI Template",
    version="0.1.0",
    description="A FastAPI template project",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(workflows_router, prefix="/api", tags=["workflows"])
app.include_router(workflows_router, prefix="/api/v1", tags=["workflows"])
