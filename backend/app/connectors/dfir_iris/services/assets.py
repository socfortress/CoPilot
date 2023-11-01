from fastapi import HTTPException

from app.connectors.dfir_iris.schema.assets import Asset
from app.connectors.dfir_iris.schema.assets import AssetResponse
from app.connectors.dfir_iris.schema.assets import AssetState
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_case


def get_case_assets(case_id: int) -> AssetResponse:
    client, case = initialize_client_and_case("DFIR-IRIS")
    result = fetch_and_validate_data(client, case.list_assets, case_id)
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
