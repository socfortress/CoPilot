from app.connectors.dfir_iris.schema.assets import Asset, AssetResponse, AssetState
from app.connectors.dfir_iris.utils.universal import (
    fetch_and_validate_data,
    initialize_client_and_case,
)
from fastapi import HTTPException


async def get_case_assets(case_id: int) -> AssetResponse:
    """
    Retrieves assets for a given case.

    Args:
        case_id (int): The ID of the case.

    Returns:
        AssetResponse: The response containing the fetched assets and their state.
    """
    client, case = await initialize_client_and_case("DFIR-IRIS")
    result = await fetch_and_validate_data(client, case.list_assets, case_id)
    try:
        asset_list = result["data"]["assets"]
        state_data = result["data"]["state"]
    except KeyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch assets for case {case_id}: {e}",
        )

    return AssetResponse(
        success=True,
        message="Successfully fetched assets for case",
        assets=[Asset(**asset) for asset in asset_list],  # List[Asset]
        state=AssetState(**state_data),  # AssetState
    )
