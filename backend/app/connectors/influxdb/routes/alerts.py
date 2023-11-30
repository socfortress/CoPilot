from typing import List

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRuleResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchResponse
from app.connectors.wazuh_indexer.services.alerts import get_alerts
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_host
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_rule
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_rule_per_host
from app.connectors.wazuh_indexer.services.alerts import get_host_alerts
from app.connectors.wazuh_indexer.services.alerts import get_index_alerts
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.influxdb.utils.universal import create_influxdb_client
from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
from app.connectors.influxdb.services.alerts import get_alerts

# App specific imports


influxdb_alerts_router = APIRouter()



@influxdb_alerts_router.get(
    "/alerts",
    response_model=InfluxDBAlertsResponse,
    description="Get influxdb alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts():
    logger.info("Fetching all alerts from influxdb")
    # client = await create_influxdb_client("InfluxDB")
    # ping = await client.ping()
    # try:
    #     query = ('''
    #         from(bucket: "_monitoring")
    #         |> range(start: -1d, stop: now())
    #         |> filter(fn: (r) => r._measurement == "statuses" and r._field == "_message")
    #         |> filter(fn: (r) => exists r._check_id and exists r._value and exists r._check_name and exists r._level)
    #         |> keep(columns: ["_time", "_value", "_check_id", "_check_name", "_level"])
    #         |> rename(columns: {"_time": "time", "_value": "message", "_check_id": "checkID", "_check_name": "checkName", "_level": "level"})
    #         |> group()
    #         |> sort(columns: ["time"], desc: true)
    #         |> limit(n: 100, offset: 29)
    #     ''')

    #     query_api = client.query_api()
    #     logger.info(f"Querying influxdb with query: {query}")
    #     result = await query_api.query(org="SOCFORTRESS", query=query)

    #     alerts = []
    #     for table in result:
    #         for record in table.records:
    #             logger.debug(f"Record: {record.values}")
    #             alerts.append({
    #                 "time": record.values.get("time").isoformat() if record.values.get("time") else None,
    #                 "message": record.values.get("message"),
    #                 "checkID": record.values.get("checkID"),
    #                 "checkName": record.values.get("checkName"),
    #                 "level": record.values.get("level")
    #             })


    #             logger.debug(f"Alerts: {alerts}")


    #     return {"alerts": alerts, "success": True, "message": "Alerts fetched successfully"}

    # except Exception as e:
    #     logger.error(f"Error fetching alerts: {e}")
    #     import traceback
    #     logger.error(traceback.format_exc())  # Log the full traceback
    #     raise HTTPException(status_code=500, detail=f"Error fetching alerts: {e}")
    # finally:
    #     await client.close()


    return await get_alerts()
