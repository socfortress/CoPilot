from flask import Blueprint, jsonify, request
from loguru import logger
from app.models.connectors import Connector, WazuhManagerConnector

from app.services.agents.agents import AgentService, AgentSyncService
from app.services.WazuhIndexer.alerts import AlertsService
from app.services.WazuhIndexer.cluster import ClusterService

bp = Blueprint("indices", __name__)


@bp.route("/indices", methods=["GET"])
