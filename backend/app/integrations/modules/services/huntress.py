import httpx
from loguru import logger

from app.integrations.modules.schema.huntress import CollectHuntress

MODULE_URL = "http://copilot-huntress-module/collect"


async def post_to_copilot_huntress_module(data: CollectHuntress, license_key: str = None) -> None:
    """
    Send a POST request to the copilot-huntress-module Docker container.

    Args:
        data (CollectHuntress): The data to send to the copilot-huntress-module Docker container.

    Raises:
        RuntimeError: if the module container is not reachable. It is an optional service and is
            deliberately not part of the default docker-compose stack, so an unresolvable
            hostname means "not deployed" far more often than it means "broken".
        httpx.HTTPStatusError: if the module answers with a non-2xx status. The response used to
            be discarded entirely, so a module that was missing or erroring still read as a
            successful collection all the way up to the scheduler's health status.
    """
    # `data` renders its credential fields as `SecretStr('**********')`; `data.to_wire()` holds
    # the real Wazuh password and Huntress API key/secret and must never be logged.
    logger.info(f"Sending POST request to {MODULE_URL} with data: {data}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MODULE_URL,
                json=data.to_wire(),
                # params={"license_key": license_key, "feature_name": "HUNTRESS"},
                timeout=120,
            )
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Could not reach the Huntress module at {MODULE_URL} ({exc}). This container is "
            "optional and is not started by the default docker-compose stack — run "
            "ghcr.io/socfortress/copilot-huntress-module:latest on the same Docker network as "
            "copilot-backend to enable Huntress collection.",
        ) from exc

    response.raise_for_status()
    return None
