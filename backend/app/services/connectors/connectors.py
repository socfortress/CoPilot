from flask import current_app
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

# from app.models.connectors import ConnectorFactory
from app.models.connectors import Connector
from app.models.connectors import connector_factory
from app.models.models import Connectors

# from app.models.models import ConnectorsAvailable
# from app.models.models import connectors_schema


class ConnectorService:
    """
    Service class for Connector operations. This class contains methods for updating and processing connectors,
    validating connector existence and data, and verifying connector connections.
    """

    def __init__(self, db):
        """
        Initializes the ConnectorService with a database session.

        Args:
            db: The database session to be used for connector operations.
        """
        self.db = db

    def update_connector_in_db(self, connector_id: int, updated_data: dict):
        """
        Updates a connector in the database with the provided data.

        Args:
            connector_id (int): The ID of the connector to update.
            updated_data (dict): The new data for the connector.

        Returns:
            dict: A dictionary containing the success status and a message indicating the status.
                  If the update operation was successful, it returns the connector name.
                  If the connector was not found, it returns a message indicating so.
                  If a database error occurred, it returns the error message.
        """
        logger.info(f"Updating connector {connector_id} with data {updated_data}")
        try:
            connector = (
                self.db.session.query(Connectors).filter_by(id=connector_id).first()
            )
            if connector:
                for key, value in updated_data.items():
                    if hasattr(connector, key):
                        setattr(connector, key, value)

                self.db.session.commit()
                return {
                    "success": True,
                    "message": f"Connector {connector_id} updated successfully",
                    "connector_name": connector.connector_name,
                }

            else:
                return {
                    "success": False,
                    "message": f"No connector found with id {connector_id}",
                }
        except SQLAlchemyError as e:
            return {"success": False, "message": f"Database error occurred: {e}"}

    def process_connector(self, connector_name: str):
        """
        Creates a connector instance, verifies the connection, and returns the connector details.

        Args:
            connector_name (str): The name of the connector to be processed.

        Returns:
            dict: A dictionary containing the name of the connector and the status of the connection verification.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        connection_details = Connector.get_connector_info_from_db(connector_name)
        logger.info(f"Connection details: {connection_details}")
        return {"name": connector_name, **connection_successful, **connection_details}

    def validate_connector_exists(self, connector_id: int):
        """
        Validates that a connector exists in the database.

        Args:
            connector_id (int): The ID of the connector to validate.

        Returns:
            dict: A dictionary containing the success status and a message indicating the status.
                  If the connector exists, it also returns the connector name.
                  If the connector was not found, it returns a message indicating so.
                  If a database error occurred, it returns the error message.
        """
        try:
            connector = (
                current_app.extensions["sqlalchemy"]
                .db.session.query(Connectors)
                .filter_by(id=connector_id)
                .first()
            )
            if connector:
                return {
                    "message": "Connector exists",
                    "connector_name": connector.connector_name,
                    "success": True,
                }
            else:
                return {
                    "message": f"No connector found with id {connector_id}",
                    "success": False,
                }
        except SQLAlchemyError as e:
            return {"message": f"Database error occurred: {e}", "success": False}

    def update_connector(self, connector_id: int, updated_data: dict):
        """
        Updates a connector in the database with the provided data.

        Args:
            connector_id (int): The ID of the connector to update.
            updated_data (dict): The new data for the connector.

        Returns:
            dict: A dictionary containing the success status and a message indicating the status.
                  If the update operation was successful, it returns the connector name.
                  If the connector was not found, it returns a message indicating so.
                  If a database error occurred, it returns the error message.
        """
        try:
            connector = (
                self.db.session.query(Connectors).filter_by(id=connector_id).first()
            )
            if connector is None:
                return {
                    "message": f"No connector found with id {connector_id}",
                    "success": False,
                }

            for key, value in updated_data.items():
                if hasattr(connector, key):
                    setattr(connector, key, value)

            self.db.session.commit()

            return {
                "message": "Connector updated successfully",
                "connector_name": connector.connector_name,
                "success": True,
            }

        except SQLAlchemyError as e:
            return {"message": f"Database error occurred: {e}", "success": False}

    def verify_connector_connection(self, connector_id: int):
        """
        Verifies the connection of a connector.

        Args:
            connector_id (int): The ID of the connector to verify.

        Returns:
            dict: A dictionary containing the success status and a message indicating the status.
                  If the connection was verified successfully, it returns the connector name and the connection status.
                  If the connector was not found, it returns a message indicating so.
                  If a database error occurred, it returns the error message.
        """
        try:
            connector = (
                self.db.session.query(Connectors).filter_by(id=connector_id).first()
            )
            if connector is None:
                return {
                    "message": f"No connector found with id {connector_id}",
                    "success": False,
                }
            connector_instance = connector_factory.create(
                connector.connector_name,
                connector.connector_name,
            )
            connection_successful = connector_instance.verify_connection()
            # Connection successful: {'connectionSuccessful': False}
            if connection_successful.get("connectionSuccessful", False) is False:
                return {
                    "message": "Connector connection failed",
                    "connector_name": connector.connector_name,
                    "success": True,
                    **connection_successful,
                }
            return {
                "message": "Connector connection verified successfully",
                "connector_name": connector.connector_name,
                "success": True,
                **connection_successful,
            }
        except SQLAlchemyError as e:
            return {"message": f"Database error occurred: {e}", "success": False}

    def validate_request_data(self, request_data: dict):
        """
        Validates the request data to ensure `connector_url`, `connector_username`, and `connector_password` are present.

        Args:
            request_data (dict): The request data to validate.

        Returns:
            dict: A dictionary containing the success status and a message indicating the status.
                  If the data is valid, it returns a message indicating so.
                  If the data is invalid, it returns a message indicating so.
        """
        if (
            request_data.get("connector_url", None)
            and request_data.get("connector_username", None)
            and request_data.get("connector_password", None)
        ):
            return {"message": "Request data is valid", "success": True}
        else:
            return {
                "message": "Request data is invalid. Ensure connector_url, connector_username and connector_password "
                "are present",
                "success": False,
            }

    def validate_request_data_api_key(self, request_data: dict):
        """
        Validates the request data to ensure `connector_url` and `connector_api_key` are present.

        Args:
            request_data (dict): The request data to validate.

        Returns:
            dict: A dictionary containing the success status and a message indicating the status.
                  If the data is valid, it returns a message indicating so.
                  If the data is invalid, it returns a message indicating so.
        """
        if request_data.get("connector_url", None) and request_data.get(
            "connector_api_key",
            None,
        ):
            return {"message": "Request data is valid", "success": True}
        else:
            return {
                "message": "Request data is invalid. Ensure connector_url and connector_api_key are present",
                "success": False,
            }
