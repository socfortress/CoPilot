from fastapi import APIRouter

from app.cloud_assessment.routes.cloud_assessment import cloud_assessment_router

# Cloud security assessment with Prowler (#1328)
router = APIRouter()

router.include_router(cloud_assessment_router, prefix="/cloud_assessment", tags=["cloud assessment"])
