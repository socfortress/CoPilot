from fastapi import APIRouter

from app.file_analysis.routes.file_analysis import file_analysis_router

# Mount the file analysis module under /api. Routes inside declare their full
# paths (/file_analysis/...), so they land at /api/file_analysis/... in line
# with the rest of the backend.
router = APIRouter()

router.include_router(file_analysis_router, tags=["file-analysis"])
