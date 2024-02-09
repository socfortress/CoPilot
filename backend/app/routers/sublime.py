from app.connectors.sublime.routes.alerts import sublime_alerts_router
from fastapi import APIRouter

# Instantiate the APIRouter
router = APIRouter()

# Include the Sublime related routes
router.include_router(sublime_alerts_router, prefix="/sublime", tags=["sublime-alerts"])
