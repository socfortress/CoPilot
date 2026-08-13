"""Keep the sidebar's InfluxDB health indicator warm (#1072).

Once every other sidebar indicator had been parallelised, this one *was* the
sidebar: a Flux query over a day of the _monitoring bucket, measured at 4.1-5.3s,
run on every load. A TTL cache did not help because `/status/sidebar` is fetched
about once per app load, so no second caller ever arrives to hit the cache.

Refreshing on a schedule moves the query off the request path entirely: the
indicator reads the last known value and this job is the only thing that waits.
The interval is shorter than the value's TTL so the sidebar never finds it
expired.
"""

from loguru import logger


async def refresh_sidebar_health() -> None:
    """Recompute the cached InfluxDB health indicator.

    Never raises: the underlying builder already converts an unreachable InfluxDB
    into a "warning" indicator, and a failure here must not stop the scheduler.
    """
    # Imported inside the function: context_indicators imports the scheduler for
    # get_scheduler_instance, so a module-level import here would be circular.
    from app.status.services.context_indicators import refresh_influx_health_indicator

    try:
        await refresh_influx_health_indicator()
        logger.debug("Sidebar InfluxDB health indicator refreshed")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not refresh the sidebar InfluxDB health indicator: {exc}")
