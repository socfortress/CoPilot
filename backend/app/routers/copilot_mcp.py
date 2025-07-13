from fastapi import APIRouter

from app.integrations.copilot_mcp.routes.copilot_mcp import copilot_mcp_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Crowdstrike related routes
router.include_router(
    copilot_mcp_router,
    prefix="/copilot_mcp",
    tags=["Copilot MCP"],
)
