import os
from datetime import datetime
from typing import List
from typing import Optional
from typing import Type
from typing import Union

import aiofiles
from fastapi import UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from werkzeug.utils import secure_filename

from app.connectors.cortex.utils.universal import verify_cortex_connection
from app.connectors.grafana.utils.universal import verify_grafana_connection
from app.connectors.graylog.utils.universal import verify_graylog_connection
from app.connectors.influxdb.utils.universal import verify_influxdb_connection
from app.connectors.models import Connectors
from app.connectors.portainer.utils.universal import verify_portainer_connection
from app.connectors.schema import ConnectorResponse
from app.connectors.shuffle.utils.universal import verify_shuffle_connection
from app.connectors.sublime.utils.universal import verify_sublime_connection
from app.connectors.velociraptor.utils.universal import verify_velociraptor_connection
from app.connectors.wazuh_indexer.utils.universal import verify_wazuh_indexer_connection
from app.connectors.wazuh_manager.utils.universal import verify_wazuh_manager_connection
from app.integrations.utils.event_shipper import verify_event_shipper_connection
from app.utils import verify_alert_creation_provisioning_connection
from app.utils import verify_haproxy_provisioning_connection
from app.utils import verify_virustotal_connection
from app.utils import verify_wazuh_worker_provisioning_connection

UPLOAD_FOLDER = "data"
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    UPLOAD_FOLDER,
)
ALLOWED_EXTENSIONS = set(["yaml"])  # replace with your allowed file extensions


# Create an interface for connector services
class ConnectorServiceInterface(BaseModel):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        raise NotImplementedError


# Wazuh Manager Service
class WazuhManagerService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_wazuh_manager_connection(connector.connector_name)


# Wazuh Indexer Service
class WazuhIndexerService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_wazuh_indexer_connection(connector.connector_name)


# Velociraptor Service
class VelociraptorService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_velociraptor_connection(connector.connector_name)


# Graylog Service
class GraylogService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_graylog_connection(connector.connector_name)


# Cortex Service
class CortexService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_cortex_connection(connector.connector_name)


# Shuffle Service
class ShuffleService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_shuffle_connection(connector.connector_name)


# Sublime Service
class SublimeService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_sublime_connection(connector.connector_name)


# InfluxDB Service
class InfluxDBService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_influxdb_connection(connector.connector_name)


# Grafana Service
class GrafanaService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_grafana_connection(connector.connector_name)


# Wazuh Worker Provisioning Service
class WazuhWorkerProvisioningService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_wazuh_worker_provisioning_connection(
            connector.connector_name,
        )


# HAProxy Provisioning Service
class HAProxyProvisioningService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_haproxy_provisioning_connection(
            connector.connector_name,
        )


# Event Shipper Service
class EventShipperService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_event_shipper_connection(connector.connector_name)


# Alert Creation Service
class AlertCreationService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_alert_creation_provisioning_connection(
            connector.connector_name,
        )


# Virustotal Service
class VirustotalService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_virustotal_connection(connector.connector_name)


# Portainer Service
class PortainerService(ConnectorServiceInterface):
    async def verify_authentication(
        self,
        connector: ConnectorResponse,
    ) -> Optional[ConnectorResponse]:
        return await verify_portainer_connection(connector.connector_name)


# Factory function to create a service instance based on connector name
def get_connector_service(connector_name: str) -> Type[ConnectorServiceInterface]:
    """
    Retrieves the service class for the given connector name.

    Args:
        connector_name (str): The name of the connector.

    Returns:
        Type[ConnectorServiceInterface]: The service class for the connector, or None if not found.
    """
    service_map = {
        "Wazuh-Manager": WazuhManagerService,
        "Wazuh-Indexer": WazuhIndexerService,
        "Velociraptor": VelociraptorService,
        "Graylog": GraylogService,
        "Cortex": CortexService,
        "Shuffle": ShuffleService,
        "Sublime": SublimeService,
        "InfluxDB": InfluxDBService,
        "Grafana": GrafanaService,
        "Wazuh Worker Provisioning": WazuhWorkerProvisioningService,
        "HAProxy Provisioning": HAProxyProvisioningService,
        "Event Shipper": EventShipperService,
        "Alert Creation Provisioning": AlertCreationService,
        "VirusTotal": VirustotalService,
        "Portainer": PortainerService,
    }
    return service_map.get(connector_name, None)


class ConnectorServices:
    """
    Service class for handling operations related to connectors.
    """

    @classmethod
    async def fetch_all_connectors(
        cls,
        session: AsyncSession,
    ) -> List[ConnectorResponse]:
        """
        Fetches all connectors from the database.

        Args:
            session (AsyncSession): The database session.

        Returns:
            List[ConnectorResponse]: A list of ConnectorResponse objects representing the fetched connectors.
        """
        try:
            result = await session.execute(select(Connectors))
        except Exception as e:
            logger.exception(f"Failed to fetch all connectors: {e}")
            exit(0)
        connectors = result.scalars().all()
        return [ConnectorResponse.from_orm(connector) for connector in connectors]

    @classmethod
    async def fetch_connector_by_id(
        cls,
        connector_id: int,
        session: AsyncSession,
    ) -> Optional[ConnectorResponse]:
        """
        Fetches a connector by its ID from the database.

        Args:
            connector_id (int): The ID of the connector to fetch.
            session (AsyncSession): The database session.

        Returns:
            Optional[ConnectorResponse]: The fetched connector, or None if not found.
        """
        result = await session.execute(
            select(Connectors).where(Connectors.id == connector_id),
        )
        connector = result.scalar_one_or_none()
        if connector:
            return ConnectorResponse.from_orm(connector)
        return None

    @classmethod
    async def fetch_connector_by_name(
        cls,
        connector_name: str,
        session: AsyncSession,
    ) -> Optional[ConnectorResponse]:
        """
        Fetches a connector by its name from the database.

        Args:
            connector_name (str): The name of the connector to fetch.
            session (AsyncSession): The database session.

        Returns:
            Optional[ConnectorResponse]: The fetched connector, or None if not found.
        """
        try:
            result = await session.execute(
                select(Connectors).where(Connectors.connector_name == connector_name),
            )
            connector = result.scalar_one_or_none()
            if connector:
                return ConnectorResponse.from_orm(connector)
            return None
        except Exception as e:
            logger.error(f"Error fetching connector by name '{connector_name}': {e}")
            return None

    @classmethod
    async def verify_connector_by_id(
        cls,
        connector_id: int,
        session: AsyncSession,
    ) -> Optional[ConnectorResponse]:
        """
        Verify a connector by making an API call to it asynchronously.

        Given a connector ID, this method retrieves the corresponding connector
        record from the database, if it exists, and makes an API call to the connector.

        Args:
            connector_id (int): The ID of the connector to verify.
            session (AsyncSession): The SQLAlchemy asynchronous session to use.

        Returns:
            Optional[ConnectorResponse]: The connector in its Pydantic representation, or None if not found.
        """
        query = select(Connectors).where(Connectors.id == connector_id)
        connector = (await session.execute(query)).scalars().first()

        if not connector:
            logger.info(f"No connector found for ID: {connector_id}")
            return None

        try:
            # Convert the SQLModel object to a Pydantic model
            connector_response = ConnectorResponse.from_orm(connector)

            # Get the appropriate service for this connector
            ServiceClass = get_connector_service(connector_response.connector_name)

            if ServiceClass is not None:
                service_instance = ServiceClass()
                # If verify_authentication is an async function, you will need to await it
                connector_response = await service_instance.verify_authentication(
                    connector_response,
                )

                # If the connector is verified, update the connector record in the database
                if connector_response["connectionSuccessful"]:
                    connector.connector_verified = True
                    connector.connector_last_updated = datetime.now()
                    session.add(connector)
                    await session.commit()
                else:
                    # If the connector is not verified, set the connector_verified field to False
                    connector.connector_verified = False
                    connector.connector_last_updated = datetime.now()
                    session.add(connector)
                    await session.commit()

            else:
                logger.error(
                    f"Connector type {connector_response.connector_name} is not supported",
                )
                return None

            return connector_response
        except Exception as e:
            logger.exception(f"Failed to create ConnectorResponse object: {e}")
            return None

    @classmethod
    async def update_connector_by_id(
        cls,
        connector_id: int,
        connector: ConnectorResponse,
        session: AsyncSession,
    ) -> Optional[ConnectorResponse]:
        """
        Update a connector by its ID in the database asynchronously.

        Given a connector ID and a Pydantic representation of a connector, this method
        updates the corresponding connector record in the database, if it exists.

        Args:
            connector_id (int): The ID of the connector to update.
            connector (ConnectorResponse): The updated connector in its Pydantic representation.
            session (AsyncSession): The SQLAlchemy asynchronous session to use.

        Returns:
            Optional[ConnectorResponse]: The updated connector in its Pydantic representation, or None if not found.
        """
        query = select(Connectors).where(Connectors.id == connector_id)
        connector_record = (await session.execute(query)).scalars().first()

        if not connector_record:
            logger.info(f"No connector found for ID: {connector_id}")
            return None

        try:
            # Update the connector record
            connector_record.connector_url = connector.connector_url
            connector_record.connector_username = connector.connector_username
            connector_record.connector_password = connector.connector_password
            connector_record.connector_api_key = connector.connector_api_key
            connector_record.connector_extra_data = connector.connector_extra_data
            connector_record.connector_last_updated = datetime.now()

            # Commit the changes to the database
            session.add(connector_record)
            await session.commit()

            # Convert the SQLModel object to a Pydantic model
            connector_response = ConnectorResponse.from_orm(connector_record)
            return connector_response
        except Exception as e:
            logger.exception(f"Failed to update connector: {e}")
            session.rollback()
            return Exception(f"Failed to update connector: {e}")

    @staticmethod
    def allowed_file(filename):
        """
        Check if a file is allowed based on its extension.

        Args:
            filename (str): The name of the file.

        Returns:
            bool: True if the file is allowed, False otherwise.
        """
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    @classmethod
    async def save_file(
        cls,
        file: UploadFile,
        connector_id: int,
        session: AsyncSession,
    ) -> Union[ConnectorResponse, bool]:
        """
        Saves the uploaded file to a specified location and updates the connector record in the database.

        Args:
            file (UploadFile): The file to be saved.
            session (AsyncSession): The async session for interacting with the database.

        Returns:
            Union[ConnectorResponse, bool]: Returns a ConnectorResponse object if the file is saved and the connector record is updated successfully.
            Otherwise, returns False.
        """
        if file and cls.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            # Save the file asynchronously
            async with aiofiles.open(file_path, "wb") as buffer:
                await buffer.write(
                    await file.read(),
                )  # Assuming file doesn't need to be read in chunks

            # Update connector using async session and ORM
            query = select(Connectors).where(Connectors.id == connector_id)
            connector_record = (await session.execute(query)).scalars().first()

            if connector_record:
                connector_record.connector_configured = True
                connector_record.connector_api_key = file_path
                session.add(connector_record)
                await session.commit()

                connector_response = ConnectorResponse.from_orm(connector_record)
                return connector_response
            else:
                return False
        else:
            return False
