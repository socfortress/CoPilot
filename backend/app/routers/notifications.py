from fastapi import APIRouter

from app.notifications.routes.notifications import notifications_router

# Mount the notifications module under /api. Routes inside this router
# already declare full paths (e.g. /customers/{code}/notification_routes,
# /notifications/dispatch) so they end up at /api/customers/... and
# /api/notifications/dispatch — matching the existing module pattern.
router = APIRouter()

router.include_router(notifications_router, tags=["notifications"])
