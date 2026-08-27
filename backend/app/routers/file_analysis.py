from fastapi import APIRouter

from app.file_analysis.routes import file_analysis_router

# Instantiate the APIRouter
router = APIRouter()

# Include the File Analysis routes
router.include_router(
    file_analysis_router,
    prefix="/file-analysis",
    tags=["File Analysis"],
)
