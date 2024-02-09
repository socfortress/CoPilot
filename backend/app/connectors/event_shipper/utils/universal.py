from typing import Optional

import asyncgelf

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


class GelfLogger:
    def __init__(self, host: str, port: str, compress: Optional[bool] = False):
        self.host = host
        self.port = port
        self.compress = compress

    async def tcp_handler(self, message):
        if not isinstance(message, dict):
            message = message.to_dict()

        handler = asyncgelf.GelfTcp(
            host=self.host,
            port=self.port,
            compress=self.compress,
        )

        response = await handler.tcp_handler(message)
        return response


async def create_gelf_logger():
    async with get_db_session() as session:
        connector_info = await get_connector_info_from_db("Event Shipper", session)
    return GelfLogger(
        host=connector_info["connector_url"],
        port=str(connector_info["connector_extra_data"]),
    )
