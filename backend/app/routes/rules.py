# from flask import jsonify
from typing import Any
from typing import Dict

from flask import Blueprint
from flask import request
from loguru import logger

from app.services.wazuh_manager.disabled_rule import DisableRuleService
from app.services.wazuh_manager.enabled_rule import EnableRuleService
from app.services.wazuh_manager.universal import UniversalService

bp = Blueprint("rules", __name__)


@bp.route("/rule/disable", methods=["POST"])
def disable_rule() -> str:
    """
    Flask route to disable a rule in Wazuh.

    This endpoint accepts a POST request with a JSON body containing the rule to be disabled.

    Returns:
        str: A JSON string response containing the updated rule information. The actual content of the response depends on the
        implementation of `DisableRuleService.disable_rule`.

    Example Request Body:
        {
            "rule_id": "200222",
            "reason": "string",
            "length_of_time": 1
        }
    """
    logger.info("Received request to disable rule")
    data: Dict[str, Any] = request.get_json()
    universal_service: UniversalService = UniversalService()
    disable_service: DisableRuleService = DisableRuleService(universal_service)
    result: str = disable_service.disable_rule(data)
    return result


@bp.route("/rule/enable", methods=["POST"])
def enable_rule() -> str:
    """
    Flask route to enable a rule in Wazuh.

    This endpoint accepts a POST request with a JSON body containing the rule to be enabled.

    Returns:
        str: A JSON string response containing the updated rule information. The actual content of the response depends on the
        implementation of `EnableRuleService.enable_rule`.

    Example Request Body:
        {
            "rule_id": "100001"
        }
    """
    logger.info("Received request to enable rule")
    data: Dict[str, Any] = request.get_json()
    universal_service: UniversalService = UniversalService()
    enable_service: EnableRuleService = EnableRuleService(universal_service)
    result: str = enable_service.enable_rule(data)
    return result
