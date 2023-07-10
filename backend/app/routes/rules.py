from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import WazuhManagerConnector
from app.models.rules import DisabledRules
from app.services.WazuhManager.disabled_rule import DisableRuleService
from app.services.WazuhManager.enabled_rule import EnableRuleService
from app.services.WazuhManager.universal import UniversalService
from app.services.WazuhManager.wazuhmanager import WazuhManagerService

bp = Blueprint("rules", __name__)


@bp.route("/rule/disable", methods=["POST"])
def disable_rule():
    """
    Endpoint to disable a rule.

    Args:
        id (str): The id of the rule to be disabled.

    Returns:
        json: A JSON response containing the updated rule information.
    """
    logger.info("Received request to disable rule")
    data = request.get_json()
    # wazuh_manager_connector = WazuhManagerConnector("Wazuh-Manager")
    # wazuh_manager_service = WazuhManagerService(wazuh_manager_connector)
    # result = wazuh_manager_service.disable_rule(data)
    # Create instance of UniversalService
    universal_service = UniversalService()
    disable_service = DisableRuleService(universal_service)
    result = disable_service.disable_rule(data)
    return result


@bp.route("/rule/enable", methods=["POST"])
def enable_rule():
    """
    Endpoint to enable a rule.

    Args:
        id (str): The id of the rule to be enabled.

    Returns:
        json: A JSON response containing the updated rule information.
    """
    logger.info("Received request to enable rule")
    data = request.get_json()
    # wazuh_manager_connector = WazuhManagerConnector("Wazuh-Manager")
    # wazuh_manager_service = WazuhManagerService(wazuh_manager_connector)
    # result = wazuh_manager_service.enable_rule(data)
    universal_service = UniversalService()
    enable_service = EnableRuleService(universal_service)
    result = enable_service.enable_rule(data)
    return result
