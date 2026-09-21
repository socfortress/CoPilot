from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

from app.db.db_session import get_db_session
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.modules.routes.huntress import collect_huntress_route
from app.integrations.modules.schema.huntress import InvokeHuntressRequest
from app.integrations.modules.schema.huntress import InvokeHuntressResponse
from app.schedulers.utils.universal import get_scheduled_job_metadata

load_dotenv()


async def invoke_huntress_integration_collect() -> InvokeHuntressResponse:
    """
    Invokes the Huntress integration collection.

    Raises:
        RuntimeError: if collection failed for any customer. `collect_huntress_route` reports a
            failure by *returning* `success=False` rather than raising, so a job that simply
            called it and returned always looked healthy to APScheduler — including when the
            module container was unreachable. Raising is what marks the run as failed:
            `last_success` is stamped centrally on EVENT_JOB_EXECUTED (see
            `app/schedulers/scheduler.py`), which fires only when the job returns normally.
    """
    logger.info("Invoking Huntress integration collection.")
    failures = []
    succeeded = 0

    async with get_db_session() as session:
        stmt = select(CustomerIntegrations).where(
            CustomerIntegrations.integration_service_name == "Huntress",
        )
        result = await session.execute(stmt)
        customer_codes = [row.customer_code for row in result.scalars()]
        logger.info(f"customer_codes: {customer_codes}")

        job_metadata = await get_scheduled_job_metadata("invoke_huntress_integration_collect")
        if job_metadata is None:
            raise RuntimeError(
                "No scheduled_job_metadata row for 'invoke_huntress_integration_collect'; cannot determine the collection interval.",
            )

        for customer_code in customer_codes:
            # One customer's failure must not stop the others: collect every outcome, then
            # decide the fate of the run as a whole.
            try:
                response = await collect_huntress_route(
                    InvokeHuntressRequest(
                        customer_code=customer_code,
                        integration_name="Huntress",
                        time_range=f"{job_metadata.time_interval}m",
                    ),
                    session,
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f"Huntress collection raised for customer {customer_code}: {e}")
                failures.append(f"{customer_code}: {e}")
                continue

            if response is None or not response.success:
                message = response.message if response is not None else "no response"
                logger.error(f"Huntress collection failed for customer {customer_code}: {message}")
                failures.append(f"{customer_code}: {message}")
            else:
                succeeded += 1

    if failures:
        raise RuntimeError(
            f"Huntress collection failed for {len(failures)} of {len(customer_codes)} customer(s): " + "; ".join(failures),
        )

    return InvokeHuntressResponse(
        success=True,
        message=f"Huntress integration invoked for {succeeded} customer(s).",
    )
