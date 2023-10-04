from datetime import datetime
from typing import List, Dict, Any, Callable, Tuple
from fastapi import HTTPException
from loguru import logger
from dfir_iris_client.case import Case
from app.connectors.dfir_iris.schema.assets import AssetResponse, Asset, AssetState
from app.connectors.dfir_iris.utils.universal import create_dfir_iris_client, fetch_and_parse_data, initialize_client_and_case, fetch_and_validate_data, handle_error


def get_case_assets(case_id: int) -> AssetResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = fetch_and_validate_data(client, case.list_assets, case_id)
    
    asset_list = result["data"]["assets"]  
    state_data = result["data"]["state"]
    
    return AssetResponse(
        success=True, 
        message="Successfully fetched assets for case", 
        assets=[Asset(**asset) for asset in asset_list],  # List[Asset]
        state=AssetState(**state_data)  # AssetState
    )

