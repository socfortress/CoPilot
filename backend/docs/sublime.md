## Sublime Overview

### <span style="color:green">Sublime Models</span>

File: sublime_alerts.py

This Python module defines a database model and corresponding schema for handling Sublime Alerts. It consists of two primary classes: `SublimeAlerts` and `SublimeAlertsSchema`.

## Class: SublimeAlerts

`SublimeAlerts` is a SQLAlchemy model class that defines a table in the database to store Sublime Alerts. Each instance of this class represents a single row in the `sublime_alerts` table.

The table has the following columns:

- `id`: This is the primary key, an integer which is unique for each alert.
- `message_id`: This is a string column, which stores the ID of the message associated with the alert.
- `timestamp`: This column stores the datetime when the alert was created. The default value is the current time in UTC.

### Methods

This class has the following methods:

- `__init__(self, message_id: str)`: This is the constructor method. It is used to initialize a new instance of the `SublimeAlerts` class with a given `message_id`.
- `__repr__(self) -> str`: This method returns a string representation of an instance of the `SublimeAlerts` class. This can be useful for debugging and logging.

## Class: SublimeAlertsSchema

`SublimeAlertsSchema` is a Marshmallow Schema class used for serializing and deserializing instances of the `SublimeAlerts` class.

### Inner Class: Meta

This class defines the fields to be serialized/deserialized. The fields are `id`, `message_id`, and `timestamp`.

### Variables: sublime_alert_schema and sublime_alerts_schema

These are instances of `SublimeAlertsSchema`. The `sublime_alert_schema` is used for single alert serialization/deserialization, while `sublime_alerts_schema` is used for multiple alerts (it has `many=True` to indicate it handles multiple objects).

::: app.models.sublime_alerts
<br>

### <span style="color:green">Sublime Routes</span>

## sublime.py - Flask Blueprint for Sublime Services

This Python file, `sublime.py`, creates a Flask Blueprint for Sublime services. It defines two HTTP endpoints related to Sublime alerts: one for storing alerts and another for retrieving alerts.

The Python classes and methods from `app.services.Sublime.alerts` and `app.services.Sublime.messages` are used to perform the core logic related to Sublime alerts.

### Blueprint Definition

The Flask Blueprint `sublime` is created at the beginning of the file, which is used to group the related endpoints.

### `/sublime/alert` Endpoint (POST)

This endpoint is used to store Sublime alerts into the `sublime_alerts` table. It's invoked by the Sublime alert webhook, which is configured in the Sublime UI.

Upon receiving a POST request, it uses the `SublimeAlertsService` to validate the payload and store the alert. If the payload is valid and is successfully stored, it returns a successful JSON response. If the payload is invalid, it logs an error and returns a failure response.

### `/sublime/alerts` Endpoint (GET)

This endpoint is used to retrieve all alerts from the `sublime_alerts` table.

Upon receiving a GET request, it uses the `SublimeAlertsService` to collect the alerts and returns them in a JSON response.

### Exception Handling

The file also defines an exception `InvalidPayloadError` which is raised when the payload received from the Sublime alert webhook is invalid. It's handled in the `put_alert()` function.

::: app.routes.sublime
<br>

### <span style="color:red">Sublime Services Alerts</span>

## alerts.py

This Python module is part of a larger application that interacts with the Sublime API and a database to handle operations related to alerts. Specifically, it receives and validates payloads from a Sublime alert webhook, stores alerts into a database, and fetches alerts from Sublime and the database.

### Classes

#### `InvalidPayloadError`

This is a custom exception class that is used to indicate that a payload received from a webhook is invalid.

#### `SublimeSession`

This class manages a session and connection to the Sublime server. It uses the requests library to create a session, updates the session headers with an authorization token and content type, and provides a method to send GET requests to a specific URL.

#### `SublimeAlertsService`

This class provides services for handling Sublime alerts. It uses an instance of the `SublimeSession` class to make HTTP requests and provides methods to perform the following operations:

- Create an instance of `SublimeAlertsService` using connector details.
- Validate a payload received from a Sublime alert webhook.
- Store an alert in the database.
- Collect alerts from Sublime and the database.
- Check whether the details for the Sublime connector were successfully collected.
- Collect alerts from the database.
- Collect alerts from Sublime.
- Handle a request error.
- Collect messages from Sublime.

The methods that start with an underscore (_) are considered private methods and are intended for internal use within the class.

Please note that this module also interacts with other parts of the larger application, such as the `db` object for interacting with the database, the `SublimeAlerts` model for the structure of the alerts, and the `UniversalService` for fetching Sublime details.

This module also logs important information and errors using the `loguru` library.

Please remember that the actual behavior of the code can depend on the rest of the application, the setup of the Sublime API, and the structure of the database.

::: app.services.Sublime.alerts
<br>

### <span style="color:red">Sublime Services Universal</span>

::: app.services.Sublime.universal
