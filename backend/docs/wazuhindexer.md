## Wazuh-Indexer Overview

### <span style="color:blue">Wazuh-Indexer Metrics Models</span>

# wazuh_indexer.py Overview

This script contains two primary components: a SQLAlchemy model class `WazuhIndexerAllocation` and a Marshmallow schema class `WazuhIndexerAllocationSchema`.

## WazuhIndexerAllocation Class

This class is a SQLAlchemy model that represents a table in a database. Each instance of this class corresponds to a row in the table. The class contains the following fields:

-   `id`: A unique integer ID for the allocation (primary key).
-   `node`: The node or host for the allocation (string, max length 100).
-   `disk_used`: The amount of disk used (floating-point number).
-   `disk_available`: The amount of disk available (floating-point number).
-   `disk_total`: The total amount of disk (floating-point number).
-   `disk_percent`: The percent of disk used (floating-point number).
-   `timestamp`: The timestamp when the allocation was created (DateTime). By default, it is the time when the entry is created.

It also includes an `__init__` method for initialization and a `__repr__` method that returns a string representation of an instance.

## WazuhIndexerAllocationSchema Class

This class is a Marshmallow schema that defines how instances of the `WazuhIndexerAllocation` class are serialized to and deserialized from JSON.

It includes a nested `Meta` class that specifies the fields to be included in the serialized/deserialized data: "id", "node", "disk_used", "disk_available", "disk_total", "disk_percent", "timestamp".

At the end of the script, it creates two schema instances: `wazuh_indexer_allocation_schema` for a single `WazuhIndexerAllocation` object, and `wazuh_indexer_allocations_schema` for multiple `WazuhIndexerAllocation` objects (specified by `many=True`).

## Purpose

This script is used to interact with a database table that tracks the disk usage on different nodes or hosts. It provides a way to create, read, update, and delete rows in this table, as well as to convert these rows to and from JSON. This can be useful, for instance, in a web service that monitors disk usage.

::: app.models.wazuh_indexer
<br>

### <span style="color:green">Alert Routes</span>

# alerts.py

This file is part of a Flask application and is responsible for defining an API endpoint related to alerts. The alerts are retrieved using the `AlertsService` and are returned in a JSON format.

## Dependencies

The file imports the following modules:

-   `Blueprint` and `jsonify` from the `flask` module.
-   `AlertsService` from the `app.services.WazuhIndexer.alerts` module.

## Blueprint

A Blueprint, `bp`, is created with the name "alerts". This Blueprint is used to register the routes and their corresponding view functions to the Flask application.

## Route: "/alerts"

This route is associated with the `get_alerts()` view function. The route listens for HTTP GET requests. When a GET request is made to the "/alerts" URL, the `get_alerts()` function is invoked.

## View Function: get_alerts()

The `get_alerts()` function retrieves all alerts from the `AlertsService`.

The process is as follows:

1. An instance of the `AlertsService` class is created.
2. The `collect_alerts()` method of the `AlertsService` instance is called to fetch all alerts.
3. The fetched alerts are returned as a JSON response.

The function is documented with a docstring that provides a brief description of its purpose, the process it follows to retrieve alerts, and the data it returns.

::: app.routes.alerts
<br>

### <span style="color:green">Wazuh-Indexer Routes</span>

# wazuhindexer.py

The `wazuhindexer.py` file is a Flask Blueprint file that sets up HTTP endpoints for interacting with the Wazuh-Indexer. Wazuh-Indexer is a security detection and response tool that indexes and correlates security data. The endpoints provide information about the indices, allocation of indices, cluster health, and shards in the Wazuh-Indexer.

The following endpoints are defined:

## GET /wazuh_indexer/indices

This endpoint lists all available indices and collects relevant information for each, including:

-   Index name
-   Index health status
-   Document count in the index
-   Size of the index
-   Number of replicas for the index

The returned JSON object contains a list of all available indices along with their respective details.

## GET /wazuh_indexer/allocation

This endpoint lists all available indices allocation, including:

-   Disk space used by the index
-   Available disk space
-   Total disk space
-   Disk usage percentage
-   Node on which the index resides

The returned JSON object contains a list of all available indices along with their respective allocation details.

## GET /wazuh_indexer/health

This endpoint collects Wazuh-Indexer cluster health information. The returned JSON object contains health information for the Wazuh-Indexer cluster.

## GET /wazuh_indexer/shards

This endpoint collects information about Wazuh-Indexer shards. The returned JSON object contains information about the shards in the Wazuh-Indexer.

The file uses services defined in `ClusterService` and `IndexService` to interact with the Wazuh-Indexer and collect the required information.

::: app.routes.wazuhindexer
<br>

### <span style="color:red">Alert Services</span>

# alerts.py

This Python module contains the `AlertsService` class, which is responsible for handling alert data from the Wazuh-Indexer.

## `AlertsService` Class

The `AlertsService` class is a service class that handles the logic of pulling alerts from the Wazuh-Indexer. It manages the connection details to the Wazuh-Indexer and provides methods to collect alerts.

### Attributes

-   `connector_url`: The URL of the Wazuh-Indexer.
-   `connector_username`: The username to authenticate with the Wazuh-Indexer.
-   `connector_password`: The password to authenticate with the Wazuh-Indexer.

The class uses the `UniversalService` class to collect connection details for the Wazuh-Indexer.

### Methods

The `AlertsService` class defines various methods for interacting with the Wazuh-Indexer. These methods include:

-   `__init__`: Initializes the `AlertsService` instance and collects Wazuh-Indexer details.
-   `_collect_alerts`: Collects alerts from the Wazuh-Indexer.
-   `_collect_alerts_details`: Collects detailed information about alerts from the Wazuh-Indexer.
-   `_handle_request_error`: Handles errors during HTTP requests to the Wazuh-Indexer.
-   `collect_alerts`: Provides a public interface for collecting alerts from the Wazuh-Indexer.

### Dependencies

The `alerts.py` file imports the following libraries and modules:

-   `typing`: For supporting type hints.
-   `elasticsearch7`: The Python client for Elasticsearch 7.
-   `loguru`: A simple and powerful logging utility.
-   `app.services.WazuhIndexer.universal`: The `UniversalService` class from the `universal` module in the `WazuhIndexer` package under `app.services`.

::: app.services.WazuhIndexer.alerts

### <span style="color:red">Cluster Services</span>

# cluster.py

This Python script defines the `ClusterService` class which provides methods for interacting with a Wazuh-Indexer's Elasticsearch cluster. The class includes methods for collecting details about the Wazuh-Indexer, initializing an Elasticsearch client, and fetching various pieces of information about the state of the cluster.

## Class: ClusterService

### Initialization

The `ClusterService` class is initialized by calling the `_collect_wazuhindexer_details()` method to collect details about the Wazuh-Indexer and then initializing the Elasticsearch client with these details.

### Methods

The class includes the following methods:

-   `_collect_wazuhindexer_details()`: Collects the details (URL, username, password) of the Wazuh-Indexer.
-   `_initialize_es_client()`: Initializes the Elasticsearch client with the collected Wazuh-Indexer details.
-   `_are_details_collected()`: Checks if all the required details for the Wazuh-Indexer have been collected.
-   `collect_node_allocation()`: Fetches the node allocation details from the Elasticsearch cluster. It returns a dictionary containing the success status, a message, and potentially the node allocation details.
-   `_collect_node_allocation()`: Handles the actual request to Elasticsearch to fetch the node allocation details. It returns a dictionary containing the success status, a message, and potentially the node allocation details.
-   `_format_node_allocation()`: Formats the node allocation details into a list of dictionaries. Each dictionary contains disk used, disk available, total disk, disk usage percentage, and node name.
-   `collect_cluster_health()`: Fetches the cluster health details from Elasticsearch. It returns a dictionary containing the success status, a message, and potentially the cluster health details.
-   `_collect_cluster_health()`: Handles the actual request to Elasticsearch to fetch the cluster health details. It returns a dictionary containing the success status, a message, and potentially the cluster health details.
-   `collect_shards()`: Fetches the shard details from the Elasticsearch cluster. It returns a dictionary containing the success status, a message, and potentially the shard details.
-   `_collect_shards()`: Handles the actual request to Elasticsearch to fetch the shard details. It returns a dictionary containing the success status, a message, and potentially the shard details.
-   `_format_shards()`: Formats the shard details into a list of dictionaries. Each dictionary contains index name, shard number, shard state, shard size, and node name.

In general, the `ClusterService` class provides an interface to query various details about the state of a Wazuh-Indexer's Elasticsearch cluster. It includes methods for collecting details about the cluster's health, node allocation, and shard distribution.

::: app.services.WazuhIndexer.cluster

### <span style="color:red">Index Services</span>

# index.py

The file `index.py` is a Python module that primarily contains the `IndexService` class. This class encapsulates the logic for interacting with a Wazuh-Indexer's Elasticsearch cluster to collect information about the indices in the cluster.

Here is a detailed breakdown of the module:

## IndexService class

This class is designed to interact with an Elasticsearch cluster, specifically a Wazuh-Indexer.

### Initialization

During the initialization of an `IndexService` object, the details of the Wazuh-Indexer are collected, and the Elasticsearch client is initialized.

### Methods

The class provides the following methods:

-   `_collect_wazuhindexer_details`: This private method collects the details of the Wazuh-Indexer, which include the connector URL, username, and password.
-   `_initialize_es_client`: This private method initializes the Elasticsearch client with the details of the Wazuh-Indexer.
-   `_are_details_collected`: This private method checks whether the details of the Wazuh-Indexer have been collected.
-   `collect_indices_summary`: This method collects summary information for each index from the Wazuh-Indexer's Elasticsearch cluster.
-   `_format_indices_summary`: This private method formats the indices summary into a list of dictionaries. Each dictionary contains the index name, health status, document count, store size, and replica count.
-   `_collect_indices`: This private method collects indices from the Wazuh-Indexer's Elasticsearch cluster. It returns a dictionary containing success status, a message, and potentially the indices.

Overall, this module is used to facilitate the interaction between the application and a Wazuh-Indexer's Elasticsearch cluster, allowing the application to collect and format summary information about the indices in the cluster.

::: app.services.WazuhIndexer.index

### <span style="color:red">Universal Services</span>

::: app.services.WazuhIndexer.universal
