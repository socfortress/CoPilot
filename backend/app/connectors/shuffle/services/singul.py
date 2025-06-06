from loguru import logger
from shufflepy import Singul

from app.connectors.shuffle.schema.singul import SingulRequest

singul = Singul(auth="REPLACE", url="https://shuffler.io")


async def execute_singul(
    request: SingulRequest,
) -> dict:
    """
    Execute a Singul integration.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing Singul integration")
    response = singul.communication.send_message(
        app=request.app,
        # org_id="REPLACE",
        auth_id="REPLACE",
        fields=[
            {"key": "to", "value": "REPLACE"},
            {"key": "subject", "value": "Test Email from Singul"},
            {"key": "body", "value": "This is a test email sent from Singul."},
        ],
    )
    logger.info(f"Singul response: {response}")
    logger.info(f"Singul response: {response.get('success', 'unknown')}")
    return {
        "executionId": response.get("id", "unknown"),
        "message": "Singul integration executed successfully",
    }
