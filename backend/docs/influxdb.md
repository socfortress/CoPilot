## InfluxDB Overview

### <span style="color:blue">Alerts Model</span>

This Python script is part of a backend service that interacts with a database to store and manage alerts coming from InfluxDB. It uses SQLAlchemy, a SQL toolkit and Object-Relational Mapping (ORM) system for Python, and Marshmallow, an ORM/ODM/framework-agnostic library for complex data types serialization, to define and manipulate a database model for the alerts.

Here is a detailed breakdown of the code:

## Import Statements

The necessary libraries and modules are imported. These include `datetime` for handling date and time information, various types from `sqlalchemy` for defining database table structure, and the `db` and `ma` instances from the `app` module.

## InfluxDBAlerts Class

This class inherits from the SQLAlchemy's `Model` class and represents the `InfluxDBAlerts` table in the database. It has four columns: `id`, `check_name`, `message`, and `timestamp`.

-   `id`: This is the primary key of the table. It is an integer.
-   `check_name`: This column stores the name of the check that triggered the alert. It is a string of up to 1000 characters.
-   `message`: This column stores the message associated with the alert. It is also a string of up to 1000 characters.
-   `timestamp`: This column stores the time when the alert was generated. It is a `DateTime` object and by default, it's set to the time when a new row is created.

The `__init__` method initializes a new instance of the class with `check_name` and `message`. The `__repr__` method returns a string representation of an instance of the class.

## InfluxDBAlertsSchema Class

This class inherits from Marshmallow's `Schema` class. It is used to serialize and deserialize instances of the `InfluxDBAlerts` class to and from Python dictionaries. This is useful for converting the model instances into a format that can be used in JSON APIs.

The `Meta` class within `InfluxDBAlertsSchema` specifies the fields to include in the serialized output.

-   `InfluxDB_alert_schema` and `InfluxDB_alerts_schema`: These are instances of the `InfluxDBAlertsSchema` class. `InfluxDB_alert_schema` is used to serialize a single `InfluxDBAlerts` instance, while `InfluxDB_alerts_schema` is used to serialize a list of `InfluxDBAlerts` instances (note the `many=True` argument).

::: app.models.influxdb_alerts
<br>

### <span style="color:green">Routes</span>

This Python script, `influxdb.py`, uses Flask to create a web server with several endpoints for handling HTTP requests related to InfluxDB checks and alerts.

Here's a detailed description:

## Import Statements

It begins by importing required modules. These include types from the `typing` module for type annotations, `Blueprint` from Flask for creating a set of routes, `jsonify` and `request` from Flask for handling JSON responses and requests, respectively, `logger` from loguru for logging, and `InfluxDBAlertsService` and `InfluxDBChecksService` from `app.services.InfluxDB`.

## Blueprint Creation

It then creates a `Blueprint` named `influxdb`. A Blueprint is a way to organize a group of related routes, and it's being used here to create routes for the InfluxDB-related endpoints.

## Route Definitions

Following this, it defines several routes:

-   `@bp.route("/influxdb/checks", methods=["GET"])`: This route responds to HTTP GET requests at the `/influxdb/checks` endpoint. It retrieves a list of all InfluxDB checks using the `InfluxDBChecksService` and returns them as a JSON response.

-   `@bp.route("/influxdb/checks/<check_id>", methods=["GET"])`: This route responds to HTTP GET requests at the `/influxdb/checks/<check_id>` endpoint. It retrieves the query of a specific InfluxDB check using the `InfluxDBChecksService` and returns it as a JSON response.

-   `@bp.route("/influxdb/alerts", methods=["GET"])`: This route responds to HTTP GET requests at the `/influxdb/alerts` endpoint. It retrieves a list of all alerts from the `influxdb_alerts` table using the `InfluxDBAlertsService` and returns them as a JSON response.

-   `@bp.route("/influxdb/alert", methods=["POST"])`: This route responds to HTTP POST requests at the `/influxdb/alert` endpoint. It stores an alert in the `influxdb_alerts` table. The endpoint is invoked by the InfluxDB alert webhook, which is configured in the InfluxDB UI. It validates the payload from the request, stores the alert if the payload is valid, and returns a JSON response indicating whether the storage was successful.

## Error Handling

If the payload of the alert to store is invalid, an exception is caught, an error message is logged, and returned as a JSON response with a 400 status code.

::: app.routes.influxdb
<br>

### <span style="color:red">Checks Services</span>

This Python script, `checks.py`, is focused on interacting with InfluxDB to manage and retrieve checks. InfluxDB checks are a part of the monitoring and alerting system, which are scripts or queries that run at regular intervals to determine the health of your data.

Here's a detailed description:

## Import Statements

The necessary libraries and modules are imported. These include types from the `typing` module for type annotations, the `requests` library for making HTTP requests, `logger` from loguru for logging, and the `UniversalService` from `app.services.InfluxDB`.

## Custom Exceptions

The script defines two custom exceptions, `InvalidPayloadError` and `ChecksCollectionError`, that are used for error handling in specific cases.

## InfluxDBSession Class

This class manages the connection and session to the InfluxDB server. It has methods to initialize the connection and to send GET requests to the server.

## InfluxDBChecksService Class

This class handles operations related to InfluxDB checks and interacts with the InfluxDB server via an `InfluxDBSession` object.

The class has methods to initialize itself with the session, connector URL, and API key. It also has a class method to create an instance of itself using connector details.

### collect_checks

This method collects all checks from InfluxDB. It sends a GET request to the InfluxDB server and processes the response to return a list of checks. Each check is a dictionary with information such as the check's ID, name, type, status, and the time it was last triggered.

### collect_check_query

This method retrieves the query for a specific check from InfluxDB. It sends a GET request to the server and processes the response to return a dictionary with the query information.

These classes and their methods provide a structured and organized way to interact with the InfluxDB server and manage InfluxDB checks.

::: app.services.InfluxDB.checks

### <span style="color:red">Alerts Services</span>

This Python script, `alerts.py`, is focused on interacting with a database to manage and retrieve alerts that come from InfluxDB.

Here's a detailed description:

## Import Statements

The necessary libraries and modules are imported. These include types from the `typing` module for type annotations, the `requests` library for making HTTP requests, `logger` from loguru for logging, `InfluxDBAlerts` from `app.models.influxdb_alerts`, and `UniversalService` from `app.services.InfluxDB`.

## Custom Exceptions

The script defines two custom exceptions, `InvalidPayloadError` and `ChecksCollectionError`, that are used for error handling in specific scenarios.

## InfluxDBSession Class

This class manages the connection and session to the InfluxDB server. It has methods to initialize the connection and to send GET requests to the server.

## InfluxDBAlertsService Class

This class handles operations related to InfluxDB alerts and interacts with the InfluxDB server via an `InfluxDBSession` object.

The class has methods to initialize itself with the session, connector URL, and API key. It also has a class method to create an instance of itself using connector details.

### validate_payload

This method validates the payload received from the InfluxDB alert webhook. If the payload is valid, it returns the check name and message. If it is invalid, it raises an `InvalidPayloadError`.

### store_alerts

This method stores the alerts in the `influxdb_alerts` table in the database.

### collect_alerts

This method collects alerts from the `influxdb_alerts` table in the database. It checks whether the InfluxDB connector details were successfully collected, then collects the alerts from the database. It returns a dictionary containing the success status, a message, and potentially the alert details.

### \_are_influxdb_details_collected

This private method checks whether the details for the InfluxDB connector were successfully collected.

### \_collect_alerts_from_db

This private method collects alerts from the `influxdb_alerts` table in the database. It returns a dictionary containing the success status, a message, and potentially the alert details.

These classes and their methods provide a structured and organized way to interact with the InfluxDB server and manage InfluxDB alerts.

::: app.services.InfluxDB.alerts

### <span style="color:red">Universal Services</span>

::: app.services.InfluxDB.universal
