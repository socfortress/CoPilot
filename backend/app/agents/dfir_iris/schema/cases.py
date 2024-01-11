from pydantic import BaseModel
from typing import List

class AssetCaseIDResponse(BaseModel):
    message: str
    success: bool
    case_ids: List[int]
