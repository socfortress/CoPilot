## Connectors Overview

### <span style="color:blue">Connectors Model</span>

This Python file, named connectors.py, primarily defines a series of connector classes that establish and verify connections with various services. Each connector class is a subclass of an abstract base class called Connector, which outlines the essential methods that each connector needs to implement.

Here is a breakdown of the main components of the file:

Connector(ABC): This is the abstract base class that outlines the essential blueprint for the connector classes. It defines an abstract method verify_connection(self) -> Dict[str, Any] that all subclasses must implement.

WazuhIndexerConnector(Connector), GraylogConnector(Connector), WazuhManagerConnector(Connector), ShuffleConnector(Connector), DfirIrisConnector(Connector), VelociraptorConnector(Connector), RabbitMQConnector(Connector): These are subclasses of the Connector class. Each subclass represents a connector for a specific service (e.g., Wazuh indexer service, Graylog service, Wazuh manager service, etc.). They implement the verify_connection(self) -> Dict[str, Any] method to establish and verify a connection with their respective service.

This module contains the following classes:

ConnectorFactory: This class is used to create instances of the connector classes. It maintains a dictionary mapping connector keys to their corresponding creator names. The register_creator method allows you to add new connector creators to the dictionary. The create method uses this dictionary to create a new connector instance based on the provided key.

dynamic_import(module_name: str, class_name: str) -> Any: This function dynamically imports a module and returns a specific class from it.

At the end of the file, an instance of the ConnectorFactory class is created and the connector creators for the seven connector classes are registered. This allows for the dynamic creation of connector instances based on the specified key.

Overall, this file provides a framework for creating and handling different types of service connectors, making it easier to establish and manage connections with various services.

::: app.models.connectors

### <span style="color:green">Connectors Routes</span>

This file, connectors.py, is a Flask blueprint module designed to define routes for operations related to connectors. Connectors are likely software components used to interact with various external systems or services, such as APIs or databases.

Here is a detailed breakdown of its functions:

list_connectors_available: An endpoint (/connectors) that uses a GET request to retrieve all available connectors. It queries the database for all connectors, dumps them into a result, and then processes each connector to instantiate it. The function returns a JSON response containing the list of all instantiated connectors.

get_connector_details: An endpoint (/connectors/<id>) that uses a GET request to retrieve the details of a specific connector, identified by its ID. It uses the ConnectorService to validate if the connector exists. If the connector exists, the function queries the database for the connector details, processes the connector to instantiate it, and returns a JSON response containing the connector details. If the connector does not exist, it returns a 404 error.

update_connector_route: An endpoint (/connectors/<id>) that uses a PUT request to update the details of a specific connector, identified by its ID. It uses the ConnectorService to validate if the connector exists and if the request data is valid. If both conditions are satisfied, the function uses the ConnectorService to update the connector in the database and then verify the connector connection. It returns a JSON response containing the connector name and the status of the connection verification. If the connector does not exist or the request data is invalid, it returns an error.

This module contains the routes related to connectors.

::: app.routes.connectors

### <span style="color:red">Connectors Services</span>

The connectors.py script is part of a service layer that handles the operations related to connector objects in the application. Connectors in this context refer to connections with external services or APIs.

Here is a detailed summary of its functionalities:

The ConnectorService class is defined to manage operations related to connectors. The service class is initialized with a database session which is used for connector operations.

The update_connector_in_db method updates a connector in the database with the provided data. It returns a dictionary containing the success status and a message indicating the status.

The process_connector method creates a connector instance, verifies the connection, and returns the connector details.

The validate_connector_exists method checks if a connector exists in the database. If the connector exists, it returns the connector name. If the connector was not found, it returns a message indicating so.

The update_connector method updates a connector in the database with the provided data. It also checks if the connector is None and returns a relevant message if true.

The verify_connector_connection method verifies the connection of a connector. If the connection was verified successfully, it returns the connector name and the connection status. If the connector was not found, it returns a message indicating so.

The validate_request_data method validates the request data to ensure connector_url, connector_username, and connector_password are present.

The validate_request_data_api_key method validates the request data to ensure connector_url and connector_api_key are present.

::: app.services.connectors.connectors
