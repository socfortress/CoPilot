## Shuffle Overview

### <span style="color:green">Shuffle Routes</span>

## shuffle.py

This is a Python file that is responsible for creating Flask routes to interact with Shuffle workflows. It is part of a larger application that presumably interacts with the Shuffle system. The Shuffle system is a security automation platform that helps automate security processes.

Here is a detailed breakdown of what the file does:

### Imports

The file imports various modules and functions that are required:

-   `Blueprint` from `flask`: This is a Flask object that allows you to create modular routes.
-   `jsonify` from `flask`: This function is used to convert Python data structures to JSON.
-   `logger` from `loguru`: This is a logging utility that provides an easy way to add log statements to your code.
-   `WorkflowsService` from `app.services.Shuffle.workflows`: This is a custom service that interacts with Shuffle workflows.

### Blueprint

A `Blueprint` named `bp` is created. This blueprint is used to create routes that are associated with Shuffle workflows.

### Routes

Four routes are created:

1. `/shuffle/workflows` (GET): This route returns a JSON response containing a list of all configured Workflows in Shuffle.
2. `/shuffle/workflows/executions` (GET): This route returns a JSON response containing the list of all configured workflows and their last execution status in Shuffle.
3. `/shuffle/workflows/executions/<workflow_id>` (GET): This route takes a `workflow_id` as an argument and returns a JSON response containing the last execution status of the specified workflow in Shuffle.

Each route creates an instance of `WorkflowsService` to interact with the Shuffle workflows.

### WorkflowsService

This is a service class that contains methods for interacting with Shuffle workflows. The methods of this class are used to collect workflows and their execution status.

In summary, the `shuffle.py` file is responsible for creating routes that provide an interface for interacting with Shuffle workflows. It uses a service class to interact with the Shuffle system and return the required data as a JSON response.

::: app.routes.shuffle
<br>

### <span style="color:red">Workflows Services</span>

## workflows.py

The `workflows.py` script is part of a larger system designed to interact with the Shuffle API, specifically to collect and manipulate information about workflows.

### Classes

#### WorkflowsService

The `WorkflowsService` class encapsulates the logic for retrieving workflow information from Shuffle. It includes methods to collect workflow details, check if details were successfully collected, send requests to the Shuffle API, and handle any exceptions that occur during these processes.

### Methods

-   `_collect_shuffle_details`: The `_collect_shuffle_details` method collects the details of the Shuffle connector from a universal service which pulls connector details from a database.

-   `_are_details_collected`: The `_are_details_collected` method checks whether the details for the Shuffle connector were successfully collected.

-   `_send_request`: The `_send_request` method sends a GET request to a provided URL.

-   `collect_workflows`: The `collect_workflows` method collects the workflows from Shuffle. If the details for the Shuffle connector were not successfully collected, the method returns a message indicating this. If the details were successfully collected, the method attempts to collect workflows from Shuffle and returns a dictionary containing the success status, a message, and potentially the workflows.

-   `_handle_request_error`: The `_handle_request_error` method handles any errors that occur during a request. It logs the error message and returns a dictionary containing the success status and an error message.

-   `_collect_workflows`: The `_collect_workflows` method attempts to collect workflows from Shuffle by sending a GET request to the appropriate Shuffle API endpoint. If the request is successful, the method returns a dictionary containing the success status, a message, and the workflows. If the request fails, the method calls the `_handle_request_error` method to handle the error.

-   `collect_workflow_details`: The `collect_workflow_details` method collects the workflow ID and workflow name from Shuffle. If the details for the Shuffle connector were not successfully collected, the method returns a message indicating this. If the details were successfully collected, the method attempts to collect workflow details from Shuffle and returns a dictionary containing the success status, a message, and potentially the workflow IDs.

-   `_collect_workflow_details`: The `_collect_workflow_details` method attempts to collect the workflow ID and workflow name from Shuffle by sending a GET request to the appropriate Shuffle API endpoint. If the request is successful, the method returns a dictionary containing the success status, a message, and the workflow IDs. If the request fails, the method calls the `_handle_request_error` method to handle the error.

-   `collect_workflow_executions_status`: The `collect_workflow_executions_status` method collects the execution status of a Shuffle Workflow by its ID. If the details for the Shuffle connector were not successfully collected, the method returns a message indicating this. If the details were successfully collected, the method attempts to collect the execution status of the workflow and returns a dictionary containing the success status, a message, and potentially the execution status.

-   `_collect_workflow_executions_status`: The `_collect_workflow_executions_status` method attempts to collect the execution status of a Shuffle Workflow by its ID by sending a GET request to the appropriate Shuffle API endpoint. If the request is successful, the method returns a dictionary containing the success status, a message, and the execution status. If the request fails, the method calls the `_handle_request_error` method to handle the error.

In summary, `workflows.py` is a script that interacts with the Shuffle API to collect and handle information about workflows. It includes robust error handling to deal with any issues that might occur during the process of interacting with the API.

::: app.services.Shuffle.workflows
<br>

### <span style="color:red">Universal Services</span>

::: app.services.Shuffle.universal
