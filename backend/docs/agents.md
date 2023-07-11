## Agents Overview

### <span style="color:blue">Agent Model</span>

# agents.py

The `agents.py` file is a Python module within a larger Flask application. It is primarily responsible for handling and managing agent metadata in the system.

## Class Definitions

### `AgentMetadata` Class

`AgentMetadata` is a SQLAlchemy model class that represents an agent's metadata. The class has the following attributes:

-   `id`: Primary key ID of an agent.
-   `agent_id`: ID of the agent.
-   `ip_address`: IP address of the agent.
-   `os`: Operating system of the agent.
-   `hostname`: Hostname of the agent.
-   `critical_asset`: A boolean flag indicating if the agent is considered a critical asset.
-   `last_seen`: The timestamp of when the agent was last seen.

In addition to these, the class defines a constructor for initializing these attributes, a `__repr__` method for providing a human-readable string representation of the instance, and several methods for manipulating the instance:

-   `mark_as_critical()`: Marks the agent as a critical asset.
-   `mark_as_non_critical()`: Marks the agent as a non-critical asset.
-   `commit_wazuh_agent_to_db()`: Commits the agent instance to the database.

### `AgentMetadataSchema` Class

`AgentMetadataSchema` is a Marshmallow Schema class used for serializing and deserializing `AgentMetadata` instances. It defines the fields that should be included when an `AgentMetadata` instance is serialized or deserialized.

## Global Variables

There are two global variables defined in the module:

-   `agent_metadata_schema`: An instance of `AgentMetadataSchema` for handling single `AgentMetadata` instances.
-   `agent_metadatas_schema`: An instance of `AgentMetadataSchema` configured for handling multiple `AgentMetadata` instances (specified with `many=True`).

## Overall Purpose

The `agents.py` module interacts with and manages agent metadata within the context of a database. Depending on the larger application, this module is used whenever the application needs to create, read, update, or delete agent metadata in the database.

::: app.models.agents
<br>

### <span style="color:green">Agent Routes</span>

# agents.py - Python Module Overview

The `agents.py` file is a Python module that primarily acts as a Flask Blueprint for defining routes related to the "agents" endpoint in a Flask web application. The main functionalities provided by this module are to list all available agents, to fetch information related to a specific agent, to sync agents, and to get agent metadata and vulnerabilities.

Below are the details of the main components and functionalities of this Python module:

## Import Section

The module starts by importing the necessary libraries, including Flask's `Blueprint` and `jsonify`, and a variety of services from the application. The services imported are:

-   `AgentService`: This service is expected to include methods that handle the main logic and operations related to the agents.
-   `AgentSyncService`: This service is expected to handle the synchronization of agents.
-   `WazuhManagerAgentService`: This service is expected to handle operations related to Wazuh Manager's agents.
-   `UniversalService`: A universal service from the Wazuh Manager.
-   `VulnerabilityService`: This service is expected to handle operations related to vulnerabilities of the agents.

## Blueprint Definition

A Flask Blueprint named "agents" is defined. This Blueprint is used to create modular components in the Flask application, in this case, all the routes related to the "agents" endpoint.

## Route Definitions

Several route decorators are used on the methods to define the endpoints for the Flask application:

-   `@bp.route("/agents", methods=["GET"])`: This route is associated with the `get_agents` function. This endpoint is expected to return a list of all agents when a GET request is made to "/agents".

-   `@bp.route("/agents/<agent_id>", methods=["GET"])`: This route is associated with the `get_agent` function. This endpoint is expected to return information related to a specific agent when a GET request is made to "/agents/<agent_id>".

-   `@bp.route("/agents/sync", methods=["POST"])`: This route is associated with the `sync_agents` function. This endpoint is expected to trigger a synchronization of the agents when a POST request is made to "/agents/sync".

-   `@bp.route("/agents/<agent_id>/metadata", methods=["GET"])`: This route is associated with the `get_agent_metadata` function. This endpoint is expected to return metadata related to a specific agent when a GET request is made to "/agents/<agent_id>/metadata".

-   `@bp.route("/agents/<agent_id>/vulnerabilities", methods=["GET"])`: This route is associated with the `get_agent_vulnerabilities` function. This endpoint is expected to return vulnerabilities related to a specific agent when a GET request is made to "/agents/<agent_id>/vulnerabilities".

Each of these methods is expected to create an instance of the respective service, call the appropriate method on the service, and return the results in JSON format using Flask's `jsonify` function. In case of an error, these methods are expected to return a JSON response with a message indicating the failure and a success status set to False.

::: app.routes.agents
<br>

### <span style="color:red">Agent Services</span>

# agents.py

This file defines two primary classes, `AgentService` and `AgentSyncService`, used for managing and synchronizing agents.

## AgentService

The `AgentService` class provides several methods for managing agent records in the application's database.

-   `get_all_agents()`: Retrieves all agents from the database.
-   `get_agent(agent_id: str)`: Retrieves a specific agent from the database using its ID.
-   `mark_agent_as_critical(agent_id: str)`: Marks a specific agent as critical.
-   `mark_agent_as_non_critical(agent_id: str)`: Marks a specific agent as non-critical.
-   `create_agent(agent: Dict[str, str])`: Creates a new agent in the database.
-   `delete_agent_db(agent_id: str)`: Deletes a specific agent from the database using its ID.

## AgentSyncService

The `AgentSyncService` class is used for synchronizing the state of agents between the application's database and the Wazuh API. It uses the `AgentService` for manipulating the agents in the database.

-   `collect_wazuh_details(connector_name: str)`: Collects the information of all Wazuh API credentials using the `WazuhIndexerConnector` class details.
-   `collect_wazuh_agents(connection_url: str, wazuh_auth_token: str)`: Collects the information of all agents from the Wazuh API.
-   `sync_agents()`: Syncs the agents between the database and the Wazuh API. It collects the agents from the Wazuh API and creates them in the database if they don't already exist.

These classes and methods allow the application to maintain a consistent state of agents between the local database and the Wazuh API.

::: app.services.agents.agents
