## Dfir-Iris Overview

### <span style="color:blue">Cases Model</span>

# cases.py

The `cases.py` file is a Python script that defines a `Case` class and a `CaseSchema` class. The file uses SQLAlchemy, a Python SQL toolkit and Object-Relational Mapping (ORM) library, to map the `Case` class to a relational database table.

## Class `Case`

The `Case` class models a 'case' in a database table. It has four fields:

-   `id` (type: Integer): Primary key of the table.
-   `case_id` (type: Integer): A unique identifier for the case.
-   `case_name` (type: String): The name of the case.
-   `agents` (type: String): A comma-separated string of agents associated with the case.

This class also has an `__init__` method for initializing a new instance of the class and an `__repr__` method that returns a string representation of a `Case` instance.

## Class `CaseSchema`

The `CaseSchema` class is a marshmallow Schema for serializing and deserializing instances of the `Case` class. The `Meta` inner class inside `CaseSchema` defines the fields to be serialized/deserialized, which are `id`, `case_id`, `case_name`, and `agents`.

This script also defines `case_schema` and `cases_schema` as instances of the `CaseSchema` class, with `cases_schema` set up to serialize/deserialize many `Case` instances at once.

::: app.models.cases
<br>

### <span style="color:green">DFIR-IRIS Routes</span>

# dfir_iris.py

This file, named `dfir_iris.py`, is a Flask module that sets up several HTTP endpoints related to the handling of case and alert data from a service named DFIR IRIS. The endpoints allow for retrieval and creation of case-related information and alert data.

Here is a detailed summary of the module:

1. The module begins by importing necessary libraries and services.

2. A Flask Blueprint named `dfir_iris` is created to register the routes.

3. A GET endpoint at `/dfir_iris/cases` is defined with the function `get_cases()`. This function retrieves all cases from the DFIR IRIS service and returns them.

4. Another GET endpoint is set up at `/dfir_iris/cases/<case_id>`, which is handled by the `get_case(case_id: str)` function. This function retrieves a specific case from the DFIR IRIS service using the provided case ID.

5. The function `get_case_notes(case_id: int)` handles GET requests at the `/dfir_iris/cases/<case_id>/notes` endpoint. It retrieves the notes associated with a specific case from the DFIR IRIS service.

6. A POST endpoint at `/dfir_iris/cases/<case_id>/note` is handled by `create_case_note(case_id: str)`. This function creates a new note for a specific case in the DFIR IRIS service.

7. The function `get_case_assets(case_id: str)` manages GET requests at the `/dfir_iris/cases/<case_id>/assets` endpoint. It retrieves the assets related to a specific case from the DFIR IRIS service.

8. Lastly, a GET endpoint at `/dfir_iris/alerts` is handled by the `get_alerts()` function. This function retrieves all alerts from the DFIR IRIS service.

Each of the functions uses a service class (like `CasesService`, `NotesService`, `AssetsService`, or `AlertsService`) to handle the interactions with the DFIR IRIS service. The data returned by these functions is sent as a JSON response to the client.

### <span style="color:green">Cases Routes</span>

::: app.routes.dfir_iris.get_cases
::: app.routes.dfir_iris.get_case
<br>

### <span style="color:green">Notes Routes</span>

::: app.routes.dfir_iris.get_case_notes
::: app.routes.dfir_iris.create_case_note
<br>

### <span style="color:green">Assets Routes</span>

::: app.routes.dfir_iris.get_case_assets
<br>

### <span style="color:green">Alerts Routes</span>

::: app.routes.dfir_iris.get_alerts
<br>

### <span style="color:red">Alerts Services</span>

# alerts.py Code Analysis

This file, named `alerts.py`, is a Python script that defines a class `AlertsService`. This class is responsible for pulling alerts from a service named DFIR-IRIS.

## Import Statements

The code begins by importing necessary modules:

-   `requests` for sending HTTP requests.
-   `loguru` for logging.
-   `UniversalService` from `app.services.DFIR_IRIS.universal`.

## Class `AlertsService`

This class appears to encapsulate all the necessary operations to pull alerts from DFIR-IRIS.

### Initialization

In the `__init__` method, an instance of `UniversalService` is created, and a session with DFIR-IRIS is initiated.

### Method `list_alerts`

This method seems to retrieve a list of all alerts from DFIR-IRIS. If the session to DFIR-IRIS is not active, it returns an error message. If the session is active, it uses the instance of `Alert` to fetch alerts from DFIR-IRIS.

## Overall

This file is part of a larger application, and its role is to interact with DFIR-IRIS to manage and retrieve alerts.

::: app.services.DFIR_IRIS.alerts
<br>

### <span style="color:red">Cases Services</span>

# cases.py

This Python module, `cases.py`, is a component of a larger application designed to interface with a tool named DFIR-IRIS. It includes a single class, `CasesService`, which is responsible for interacting with DFIR-IRIS to retrieve case information.

## CasesService class

The `CasesService` class has the following methods:

### `__init__` method

This method initializes the `CasesService` class. It creates an instance of `UniversalService` and attempts to establish a session with DFIR-IRIS. If the session creation fails, it logs the failure message and sets `self.iris_session` to `None`.

### `list_cases` method

This method fetches a list of all cases from DFIR-IRIS. If a session has not been established successfully, it returns a failure message. If a session is available, it uses the `Case` class from the `dfir_iris_client.case` module to retrieve a list of cases. If the case retrieval process fails, it logs an error and returns a failure status. If the case retrieval is successful, it returns a dictionary containing a success status, a success message, and the retrieved case data.

::: app.services.DFIR_IRIS.cases
<br>

### <span style="color:red">Assets Services</span>

# assets.py

The `assets.py` script contains the `AssetsService` class, which provides the logic for pulling case assets from DFIR-IRIS. It creates a DFIR-IRIS session upon initialization and uses it to fetch case assets.

## Class Initialization

The class is initialized by creating a `UniversalService` object for DFIR-IRIS and establishing a session. If the session creation is unsuccessful, an error is logged, and the `iris_session` attribute is set to None.

## Method: get_case_assets

The `get_case_assets` method retrieves the assets of a specific case from DFIR-IRIS. If the `iris_session` attribute is None (indicating that the session creation was unsuccessful), this method returns a dictionary with `"success"` set to `False`. Otherwise, it attempts to fetch and parse the assets data for the case specified by the `cid` parameter.

The return value is a dictionary containing the success status, a message, and potentially the fetched assets. The `"success"` key is a boolean indicating whether the operation was successful. The `"message"` key is a string providing details about the operation. If `"success"` is `True`, the dictionary also contains the `"data"` key with the fetched assets.

::: app.services.DFIR_IRIS.assets
<br>

### <span style="color:red">Notes Services</span>

# notes.py

The `notes.py` file defines a `NotesService` class that encapsulates the logic for interacting with case notes from DFIR-IRIS. Here is a detailed breakdown of the file:

## Class: NotesService

The `NotesService` class is designed to manage case notes from DFIR-IRIS. This includes operations like retrieving and creating case notes. The class utilizes a session with DFIR-IRIS to execute these operations.

### Initializer

The class initializer (`__init__`) creates an instance of `UniversalService` for "DFIR-IRIS" and attempts to establish a session with DFIR-IRIS. If the session cannot be established, it logs an error message and sets the `iris_session` attribute to `None`.

### Method: get_case_notes

This method retrieves the notes of a specific case from DFIR-IRIS. It takes two parameters: `search_term` and `cid` (the ID of the case to retrieve notes for). The method checks if the `iris_session` is `None` (indicating unsuccessful session creation), and if so, returns a dictionary indicating failure. Otherwise, it fetches and parses the notes data for the specified case.

### Method: \_get_case_note_details

This private method retrieves the details of a specific note of a case from DFIR-IRIS. It takes two parameters: `note_id` and `cid` (the ID of the note and the ID of the case respectively). Similar to `get_case_notes`, this method checks if the `iris_session` is `None` and returns a dictionary indicating failure if so. If the session exists, it fetches and parses the note data for the specified note and case.

### Method: create_case_note

This method creates a note for a specific case in DFIR-IRIS. It takes three parameters: `cid` (the ID of the case), `note_title` (the title of the note to create), and `note_content` (the content of the note to create). Like the other methods, it checks if the `iris_session` is `None` and returns a dictionary indicating failure if so. If the session exists, it attempts to create a note with the specified title and content for the specified case.

This file serves as a core component in managing case notes in DFIR-IRIS, providing functionalities to fetch, parse, and create notes. It demonstrates a good encapsulation of related operations into a dedicated service class, thereby promoting code organization and maintainability.

::: app.services.DFIR_IRIS.notes
<br>

### <span style="color:red">Universal Services</span>

::: app.services.DFIR_IRIS.universal
<br>
