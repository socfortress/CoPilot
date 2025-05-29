from loguru import logger
from shufflepy import Singul
from app.connectors.shuffle.schema.singul import SingulRequest
from app.connectors.shuffle.utils.universal import send_post_request

singul = Singul(auth="TEMP", url="https://singul.io")

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
        fields=[
            {"key": "to", "value": "walton.taylor23@gmail.com"},
            {"key": "subject", "value": "Test Email from Singul"},
            {"key": "body", "value": "This is a test email sent from Singul."},
        ]
    )
    logger.info(f"Singul response: {response}")
    return {
        "executionId": response.get("id", "unknown"),
        "message": "Singul integration executed successfully",
    }

