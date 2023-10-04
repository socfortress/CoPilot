from datetime import datetime
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Tuple

from dfir_iris_client.case import Case
from fastapi import HTTPException
from loguru import logger

from app.connectors.dfir_iris.schema.assets import Asset
from app.connectors.dfir_iris.schema.assets import AssetResponse
from app.connectors.dfir_iris.schema.assets import AssetState
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client
from app.connectors.dfir_iris.utils.universal import fetch_and_parse_data
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import handle_error
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case


def get_case_assets(case_id: int) -> AssetResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = fetch_and_validate_data(client, case.list_assets, case_id)

    asset_list = result["data"]["assets"]
    state_data = result["data"]["state"]

    return AssetResponse(
        success=True,
        message="Successfully fetched assets for case",
        assets=[Asset(**asset) for asset in asset_list],  # List[Asset]
        state=AssetState(**state_data),  # AssetState
    )
