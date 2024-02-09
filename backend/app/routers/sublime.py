from fastapi import APIRouter

from app.connectors.sublime.routes.alerts import sublime_alerts_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Sublime related routes
router.include_router(sublime_alerts_router, prefix="/sublime", tags=["sublime-alerts"])
