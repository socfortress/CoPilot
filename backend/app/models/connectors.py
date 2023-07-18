import importlib
import json
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Dict

import grpc
import pika
import pyvelociraptor
import requests
from elasticsearch7 import Elasticsearch
from flask import current_app
from loguru import logger
from pyvelociraptor import api_pb2
from pyvelociraptor import api_pb2_grpc
from sqlalchemy.orm.exc import NoResultFound

from app.models.models import Connectors


def dynamic_import(module_name: str, class_name: str) -> Any:
    """
    This function dynamically imports a module and returns a specific class from it.

    :param module_name: A string that specifies the name of the module to import.
    :param class_name: A string that specifies the name of the class to get from the module.
    :return: The class specified by class_name from the module specified by module_name.
    """
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_


@dataclass
class Connector(ABC):
    """
    This abstract base class defines the interface for a connector. A connector is an object that
    connects to a specific service or system and performs actions on it. The specific service or
    system a connector connects to is defined by the connector's attributes.

    :param attributes: A dictionary of attributes necessary for the connector to connect to the service or system.
    """

    attributes: Dict[str, Any]

    @abstractmethod
    def verify_connection(self) -> Dict[str, Any]:
        """
        This abstract method should be implemented by all subclasses of Connector. It is meant to verify the
        connection to the service or system the connector is designed to connect to.

        :return: Depends on the implementation in the subclass.
        """
        pass

    @staticmethod
    def get_connector_info_from_db(connector_name: str) -> Dict[str, Any]:
        """
        This method retrieves connector information from the database.

        :param connector_name: A string that specifies the name of the connector whose information is to be retrieved.
        :return: A dictionary of the connector's attributes if the connector exists. Otherwise, it raises a
        NoResultFound exception.
        Raises:
            NoResultFound: If the connector_name is not found in the database.
        """
        connector = current_app.extensions["sqlalchemy"].db.session.query(Connectors).filter_by(connector_name=connector_name).first()
        if connector:
            attributes = {col.name: getattr(connector, col.name) for col in Connectors.__table__.columns}
            return attributes
        else:
            raise NoResultFound


class WazuhIndexerConnector(Connector):
    """
    This class represents a connector for the Wazuh indexer service. It is a subclass of Connector.

    :param connector_name: A string that specifies the name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        This method verifies the connection to the Wazuh indexer service.

        :return: A dictionary containing the status of the connection attempt and information about
        the cluster's health.
        """
        logger.info(
            f"Verifying the wazuh-indexer connection to {self.attributes['connector_url']}",
        )
        try:
            es = Elasticsearch(
                [self.attributes["connector_url"]],
                http_auth=(
                    self.attributes["connector_username"],
                    self.attributes["connector_password"],
                ),
                verify_certs=False,
                timeout=15,
                max_retries=10,
                retry_on_timeout=False,
            )
            es.cluster.health()
            logger.info(f"Connection to {self.attributes['connector_url']} successful")
            return {"connectionSuccessful": True}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "clusterHealth": None}


class GraylogConnector(Connector):
    """
    This class represents a connector for the Graylog service. It is a subclass of Connector.

    :param connector_name: A string that specifies the name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to Graylog service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'roles' if the connection is successful.
        """
        logger.info(
            f"Verifying the graylog connection to {self.attributes['connector_url']}",
        )
        try:
            graylog_roles = requests.get(
                f"{self.attributes['connector_url']}/api/authz/roles/user/{self.attributes['connector_username']}",
                auth=(
                    self.attributes["connector_username"],
                    self.attributes["connector_password"],
                ),
                verify=False,
            )
            if graylog_roles.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {graylog_roles.text}",
                )
                return {"connectionSuccessful": False, "roles": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "roles": None}


class WazuhManagerConnector(Connector):
    """
    This class represents a connector for the Wazuh manager service. It is a subclass of Connector.

    :param connector_name: A string that specifies the name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to Wazuh manager service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
        """
        logger.info(
            f"Verifying the wazuh-manager connection to {self.attributes['connector_url']}",
        )
        try:
            wazuh_auth_token = requests.get(
                f"{self.attributes['connector_url']}/security/user/authenticate",
                auth=(
                    self.attributes["connector_username"],
                    self.attributes["connector_password"],
                ),
                verify=False,
            )
            if wazuh_auth_token.status_code == 200:
                logger.debug("Wazuh Authentication Token successful")
                wazuh_auth_token = wazuh_auth_token.json()
                wazuh_auth_token = wazuh_auth_token["data"]["token"]
                return {"connectionSuccessful": True, "authToken": wazuh_auth_token}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {wazuh_auth_token.text}",
                )
                return {"connectionSuccessful": False, "authToken": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "authToken": None}

    def get_auth_token(self) -> str:
        """
        Returns the authentication token for the Wazuh manager service.

        Returns:
            str: Authentication token for the Wazuh manager service.
        """
        return self.verify_connection()["authToken"]


class ShuffleConnector(Connector):
    """
    This class represents a connector for the Shuffle service. It is a subclass of Connector.

    :param connector_name: A string that specifies the name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to Shuffle service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'apps' if the connection is successful.
        """
        logger.info(
            f"Verifying the shuffle connection to {self.attributes['connector_url']}",
        )
        try:
            headers = {
                "Authorization": f"Bearer {self.attributes['connector_api_key']}",
            }
            shuffle_apps = requests.get(
                f"{self.attributes['connector_url']}/api/v1/apps",
                headers=headers,
                verify=False,
            )
            if shuffle_apps.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {shuffle_apps.text}",
                )
                return {"connectionSuccessful": False}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False}


class DfirIrisConnector(Connector):
    """
    This class represents a connector for the DFIR IRIS service. It is a subclass of Connector.

    :param connector_name: A string that specifies the name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to DFIR IRIS service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'response' if the connection is successful.
        """
        logger.info(
            f"Verifying the dfir-iris connection to {self.attributes['connector_url']}",
        )
        try:
            headers = {
                "Authorization": f"Bearer {self.attributes['connector_api_key']}",
            }
            dfir_iris = requests.get(
                f"{self.attributes['connector_url']}/api/ping",
                headers=headers,
                verify=False,
            )
            # See if 200 is returned
            if dfir_iris.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {dfir_iris.text}",
                )
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "response": None}


class VelociraptorConnector(Connector):
    """
    A connector for the Velociraptor service, a subclass of Connector.

    Args:
        connector_name (str): The name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to Velociraptor service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'response' if the connection is successful.
        """
        try:
            connector_api_key = self.attributes["connector_api_key"]

            with open(connector_api_key, "r") as f:
                f.read()

            try:
                config = pyvelociraptor.LoadConfigFile(connector_api_key)
                creds = grpc.ssl_channel_credentials(
                    root_certificates=config["ca_certificate"].encode("utf8"),
                    private_key=config["client_private_key"].encode("utf8"),
                    certificate_chain=config["client_cert"].encode("utf8"),
                )

                options = (("grpc.ssl_target_name_override", "VelociraptorServer"),)

                with grpc.secure_channel(
                    config["api_connection_string"],
                    creds,
                    options,
                ) as channel:
                    stub = api_pb2_grpc.APIStub(channel)
                    client_query = "SELECT * FROM info()"

                    client_request = api_pb2.VQLCollectorArgs(
                        max_wait=60,
                        Query=[
                            api_pb2.VQLRequest(
                                Name="ClientQuery",
                                VQL=client_query,
                            ),
                        ],
                    )

                    r = []
                    for response in stub.Query(client_request):
                        if response.Response:
                            r = r + json.loads(response.Response)
                    return {"connectionSuccessful": True}
            except Exception as e:
                logger.error(f"Failed to verify connection to Velociraptor: {e}")
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(f"Failed to get connector_api_key from the database: {e}")
            return {"connectionSuccessful": False, "response": None}


class SublimeConnector(Connector):
    """
    A connector for the Sublime service, a subclass of Connector.

    Args:
        connector_name (str): The name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to Sublime service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'response' if the connection is successful.
        """
        logger.info(
            f"Verifying the sublime connection to {self.attributes['connector_url']}",
        )
        try:
            headers = {
                "Authorization": f"Bearer {self.attributes['connector_api_key']}",
                "Content-Type": "application/json",
            }
            params = {"limit": 1}
            sublime = requests.get(
                f"{self.attributes['connector_url']}/v0/rules",
                headers=headers,
                params=params,
                verify=False,
            )
            if sublime.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {sublime.text}",
                )
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "response": None}


class AskSOCFortressConnector(Connector):
    """
    A connector for the ASK SOCFortress service, a subclass of Connector.

    Args:
        connector_name (str): The name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to ASK SOCFortress service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'response' if the connection is successful.
        """
        logger.info(
            f"Verifying the ASK SOCFortress connection to {self.attributes['connector_url']}",
        )
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": f"{self.attributes['connector_api_key']}",
                "module-version": "1.0",
            }
            payload = {
                "rule_description": "Summary event of the report's signatures.",
            }
            ask_socfortress = requests.post(
                f"{self.attributes['connector_url']}",
                headers=headers,
                data=json.dumps(payload),
                verify=False,
                timeout=60,
            )
            if ask_socfortress.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {ask_socfortress.text}",
                )
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "response": None}


class SocfortressThreatIntelConnector(Connector):
    """
    A connector for the SocfortressThreatIntel service, a subclass of Connector.

    Args:
        connector_name (str): The name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to ASK SOCFortress service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'response' if the connection is successful.
        """
        logger.info(
            f"Verifying the ASK SOCFortress connection to {self.attributes['connector_url']}",
        )
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": f"{self.attributes['connector_api_key']}",
                "module-version": "1.0",
            }
            params = {
                "value": "evil.socfortress.co",
            }
            socfortress_threat_intel = requests.get(
                f"{self.attributes['connector_url']}",
                headers=headers,
                params=params,
                verify=False,
                timeout=60,
            )
            if socfortress_threat_intel.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {socfortress_threat_intel.text}",
                )
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "response": None}


class InfluxDBConnector(Connector):
    """
    A connector for the InfluxDB service, a subclass of Connector.

    Args:
        connector_name (str): The name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to InfluxDB service.

        Returns:
            dict: A dictionary containing 'connectionSuccessful' status and 'response' if the connection is successful.
        """
        logger.info(
            f"Verifying the InfluxDB connection to {self.attributes['connector_url']}",
        )
        try:
            headers = {
                "Authorization": f"Token {self.attributes['connector_api_key']}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            influxdb = requests.get(
                f"{self.attributes['connector_url']}/api/v2/buckets",
                headers=headers,
                verify=False,
            )
            if influxdb.status_code == 200:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(
                    f"Connection to {self.attributes['connector_url']} failed with error: {influxdb.text}",
                )
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "response": None}


class RabbitMQConnector(Connector):
    """
    A connector for the RabbitMQ service, a subclass of Connector.

    Args:
        connector_name (str): The name of the connector.
    """

    def __init__(self, connector_name: str):
        super().__init__(attributes=self.get_connector_info_from_db(connector_name))

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verifies the connection to RabbitMQ service.
        """
        logger.info(
            f"Verifying the rabbitmq connection to {self.attributes['connector_url']}",
        )
        try:
            # For the connector_url, strip out the host and port and use that for the connection
            # This is because the connection string is not in the format that pika expects
            connector_host, connector_port = self.attributes["connector_url"].split(":")
            connector_port = int(connector_port)

            credentials = pika.PlainCredentials(
                self.attributes["connector_username"],
                self.attributes["connector_password"],
            )
            parameters = pika.ConnectionParameters(
                connector_host,
                connector_port,
                credentials=credentials,
            )
            connection = pika.BlockingConnection(parameters)
            if connection.is_open:
                logger.info(
                    f"Connection to {self.attributes['connector_url']} successful",
                )
                return {"connectionSuccessful": True}
            else:
                logger.error(f"Connection to {self.attributes['connector_url']} failed")
                return {"connectionSuccessful": False, "response": None}
        except Exception as e:
            logger.error(
                f"Connection to {self.attributes['connector_url']} failed with error: {e}",
            )
            return {"connectionSuccessful": False, "response": None}


class ConnectorFactory:
    """
    This class represents a factory for creating connector instances.

    :param creators: A dictionary mapping connector keys to their corresponding creator names.
    """

    def __init__(self):
        """
        Initialize a new instance of the ConnectorFactory.
        """
        self._creators = {}

    def register_creator(self, key, creator):
        """
        Register a new connector creator.

        :param key: The key of the connector.
        :param creator: The creator of the connector.
        """
        self._creators[key] = creator

    def create(self, key, connector_name):
        """
        Create a new connector instance.

        :param key: The key of the connector.
        :param connector_name: The name of the connector.

        :return: A new instance of the connector.

        :raises ValueError: If the key is not found in the list of creators.
        """
        creator = self._creators.get(key)
        if not creator:
            raise ValueError(key)
        # use dynamic_import to get the class and initialize it
        connector_class = dynamic_import("app.models.connectors", creator)
        return connector_class(connector_name)


# Instantiate factory
connector_factory = ConnectorFactory()


# Register connector creators
connector_factory.register_creator("Wazuh-Indexer", "WazuhIndexerConnector")
connector_factory.register_creator("Graylog", "GraylogConnector")
connector_factory.register_creator("Wazuh-Manager", "WazuhManagerConnector")
connector_factory.register_creator("DFIR-IRIS", "DfirIrisConnector")
connector_factory.register_creator("Velociraptor", "VelociraptorConnector")
connector_factory.register_creator("RabbitMQ", "RabbitMQConnector")
connector_factory.register_creator("Shuffle", "ShuffleConnector")
connector_factory.register_creator("Sublime", "SublimeConnector")
connector_factory.register_creator("InfluxDB", "InfluxDBConnector")
connector_factory.register_creator("AskSocfortress", "AskSOCFortressConnector")
connector_factory.register_creator("SocfortressThreatIntel", "SocfortressThreatIntelConnector")
