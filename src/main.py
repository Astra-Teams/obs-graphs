from fastapi import FastAPI

from src.api.v1.routers.workflows import router as workflows_router

app = FastAPI(
    title="FastAPI Template",
    version="0.1.0",
    description="A FastAPI template project",
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
