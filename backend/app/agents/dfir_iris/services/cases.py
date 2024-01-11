from fastapi import HTTPException
from loguru import logger


from app.connectors.dfir_iris.services.cases import get_all_cases
from app.connectors.dfir_iris.schema.cases import CaseResponse

from app.connectors.dfir_iris.services.cases import get_all_cases
