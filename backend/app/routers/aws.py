from fastapi import APIRouter

from app.integrations.aws.routes.provision import integration_aws_router

# Instantiate the APIRouter
router = APIRouter()

# Include the AWS related routes
router.include_router(
    integration_aws_router,
    prefix="/aws",
    tags=["AWS"],
)
