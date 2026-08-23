"""Assemble the sidebar's deployment-wide indicators off the request path (#1072).

Twelve of the sidebar's fourteen indicators give the same answer for every user.
Recomputing them inside each request is what kept `/status/sidebar` at ~3s even
after they were parallelised: not one slow builder, but a dozen database
round-trips contending for connections, all finishing at about the same time.

This job pays for them once; requests read the result from memory and compute
only the two genuinely per-user indicators (whose alerts, whose cases).
"""

from loguru import logger


async def refresh_sidebar_indicators() -> None:
    """Recompute the cached deployment-wide sidebar indicators.

    Never raises: each builder is already wrapped in `safe_build`, so an
    unreachable service degrades one indicator rather than failing the job.
    """
    # Imported inside the function: context imports the scheduler for
    # get_scheduler_instance, so a module-level import here would be circular.
    from app.status.services.context import refresh_shared_indicators

    try:
        await refresh_shared_indicators()
        logger.debug("Sidebar shared indicators refreshed")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not refresh the sidebar shared indicators: {exc}")
