from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
@router.get("/")
def health_check():
    """Simple health check endpoint for container orchestration and monitoring."""
    return {"status": "ok"}
