from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import WazuhManagerConnector
from app.services.agents.agents import AgentService
from app.services.agents.agents import AgentSyncService
from app.services.WazuhIndexer.alerts import AlertsService
from app.services.WazuhIndexer.cluster import ClusterService

bp = Blueprint("indices", __name__)


@bp.route("/indices", methods=["GET"])
