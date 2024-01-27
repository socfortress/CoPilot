from typing import List

from pydantic import BaseModel


class AssetCaseIDResponse(BaseModel):
    message: str
    success: bool
    case_ids: List[int]
