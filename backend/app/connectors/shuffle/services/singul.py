from loguru import logger

from app.connectors.shuffle.schema.singul import SingulRequest
from app.connectors.shuffle.utils.universal import get_shuffle_org_id
from app.connectors.shuffle.utils.universal import get_singul_client

# async def execute_singul(
#     request: SingulRequest,
# ) -> dict:
#     """
#     Execute a Singul integration.

#     Args:
#         request (SingulRequest): The request object containing the workflow ID.

#     Returns:
#         dict: The response containing the execution ID.
#     """
#     logger.info("Executing Singul integration")

#     # Get Singul client from database credentials
#     singul = await get_singul_client()

#     try:
#         response = singul.connect(
#             app=request.app,
#             action="send_message",
#             org_id=await get_shuffle_org_id(),
#             environment="REPLACE_ME",
#             fields=[
#                 {"key": "to", "value": "walton.taylor23@gmail.com"},
#                 {"key": "subject", "value": "Test Email from Singul"},
#                 {"key": "body", "value": "This is a test email sent from Singul."},
#             ],
#         )
#         logger.info(f"Singul response: {response}")
#         logger.info(f"Singul response success: {response.get('success', 'unknown')}")

#         return {
#             "executionId": response.get("id", "unknown"),
#             "message": "Singul integration executed successfully",
#         }
#     except Exception as e:
#         logger.error(f"Failed to execute Singul integration: {e}")
#         return {"executionId": "unknown", "message": f"Singul integration failed: {e}", "success": False}


async def execute_singul(
    request: SingulRequest,
) -> dict:
    """
    Execute a Singul integration.

    Args:
        request (SingulRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing Singul integration")

    # Get Singul client from database credentials
    singul = await get_singul_client()

    try:
        response = singul.connect(
            app="opencti",
            action="get_ioc",
            org_id=await get_shuffle_org_id(),
            environment="THREATINTEL",
            fields=[{"key": "ip", "value": "185.215.113.75"}],
        )
        logger.info(f"Singul response: {response}")
        logger.info(f"Singul response success: {response.get('success', 'unknown')}")

        return {
            "executionId": response.get("id", "unknown"),
            "message": "Singul integration executed successfully",
        }
    except Exception as e:
        logger.error(f"Failed to execute Singul integration: {e}")
        return {"executionId": "unknown", "message": f"Singul integration failed: {e}", "success": False}
