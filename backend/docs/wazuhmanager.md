## Wazuh-Manager Overview

### <span style="color:blue">Wazuh-Manager Model Rules</span>

## rules.py Markdown Explanation

The `rules.py` file appears to be a Python module that defines a SQLAlchemy model and a Marshmallow schema for representing and serializing/deserializing disabled rules in a system.

### Imports

The script imports necessary modules at the beginning:

-   `datetime`: A standard Python module for handling dates and times.
-   `sqlalchemy`: A popular SQL toolkit and ORM for Python.
-   `app`: The application module, presumably containing the SQLAlchemy and Marshmallow instances.

### Class Definition: DisabledRules

The `DisabledRules` class is a SQLAlchemy model that represents disabled rules in a system. It includes the following fields:

-   `id`: Unique integer ID of the rule.
-   `rule_id`: ID of the rule.
-   `previous_level`: Previous level configuration of the rule.
-   `new_level`: New level configuration of the rule.
-   `reason_for_disabling`: Reason for disabling the rule.
-   `date_disabled`: Date when the rule was disabled.
-   `length_of_time`: Length of time the rule will be disabled for.

The `__init__` method initializes a new instance of the `DisabledRules` class, and the `__repr__` method returns a string representation of the `DisabledRules` instance.

### Class Definition: DisabledRulesSchema

The `DisabledRulesSchema` class is a Marshmallow schema that is used to serialize and deserialize instances of the `DisabledRules` class. The `Meta` inner class defines the fields to be included in the serialized/deserialized data.

The script also defines two instances of the `DisabledRulesSchema` class:

-   `disabled_rule_schema`: Used for serializing/deserializing a single `DisabledRules` instance.
-   `disabled_rules_schema`: Used for serializing/deserializing a list of `DisabledRules` instances.

This script follows good practices for defining SQLAlchemy models and Marshmallow schemas. Each class and method is well-documented with a docstring that describes its purpose, the arguments it accepts (if any), and what it returns.

::: app.models.rules

### <span style="color:blue">Wazuh-Manager Model Agents</span>

::: app.models.agents
<br>

### <span style="color:green">Wazuh-Manager Routes</span>

::: app.routes.agents.sync_agents
::: app.routes.agents.delete_agent
::: app.routes.agents.get_agent_vulnerabilities
<br>

### <span style="color:red">Wazuh-Manager Services Agents</span>

## agent.py Markdown Explanation

The `agent.py` file appears to be a Python module that defines two classes: `WazuhHttpRequests` and `WazuhManagerAgentService`. These classes encapsulate the functionality for interacting with the Wazuh Manager agent system.

### Imports

The script imports necessary modules at the beginning:

-   `requests`: A popular Python library used for making HTTP requests.
-   `loguru`: A third-party library providing a more convenient and powerful logger for Python.
-   `typing`: A standard Python library for support of type hints.
-   `app.services.WazuhManager.universal.UniversalService`: The `UniversalService` class from the `app.services.WazuhManager.universal` module.

### Class Definition: WazuhHttpRequests

The `WazuhHttpRequests` class handles HTTP requests to the Wazuh API. It is initialized with the URL for the Wazuh connector and an authentication token. It provides a method to make HTTP DELETE requests to the specified Wazuh API endpoint.

### Class Definition: WazuhManagerAgentService

The `WazuhManagerAgentService` class encapsulates the logic for handling agent-related operations in the Wazuh Manager. It uses the `UniversalService` to get authentication tokens and URLs, and `WazuhHttpRequests` to make HTTP requests.

It provides methods to:

-   Collect all agents from Wazuh Manager (`collect_agents` method).
-   Delete a specific agent (`delete_agent` method).

Helper Methods

Several private methods are also defined to support the main functionality:

-   `_get_agent_data`: Retrieves agent data from the Wazuh Manager.
-   `_build_agent_list`: Builds a list of dictionaries with agent data.

Error Handling

The script includes error handling using try/except blocks. When an error occurs, the error message is logged using loguru's `logger.error` function, and a dictionary with a failure message and success status set to False is returned.

The `WazuhHttpRequests` and `WazuhManagerAgentService` classes appear to be well-structured and follow good practices for encapsulating functionality related to Wazuh's agent system. Each class and method is well-documented with a docstring that describes its purpose, the arguments it accepts (if any), and what it returns.

::: app.services.WazuhManager.agent

### <span style="color:red">Wazuh-Manager Services Disabled Rule</span>

## disabled_rule.py Markdown Explanation

The `disabled_rule.py` file appears to be a Python module that defines two classes: `WazuhHttpRequests` and `DisableRuleService`. These classes encapsulate the functionality for interacting with the Wazuh Manager rules system, specifically for disabling rules.

### Imports

The script imports necessary modules at the beginning:

-   `requests`: A popular Python library used for making HTTP requests.
-   `loguru`: A third-party library providing a more convenient and powerful logger for Python.
-   `typing`: A standard Python library for support of type hints.
-   `xmltodict`: A Python module that makes working with XML feel like you are working with JSON.
-   `app.models.rules.DisabledRules`: The `DisabledRules` class from the `app.models.rules` module.
-   `app.services.WazuhManager.universal.UniversalService`: The `UniversalService` class from the `app.services.WazuhManager.universal` module.

### Class Definition: WazuhHttpRequests

The `WazuhHttpRequests` class handles HTTP requests to the Wazuh API. It is initialized with the URL for the Wazuh connector and an authentication token. It provides methods to make HTTP GET and PUT requests to the specified Wazuh API endpoint.

### Class Definition: DisableRuleService

The `DisableRuleService` class encapsulates the logic for handling rule-disabling operations in the Wazuh Manager. It uses the `UniversalService` to get authentication tokens and URLs, and `WazuhHttpRequests` to make HTTP requests.

It provides a method to disable a specific rule in the Wazuh Manager (`disable_rule` method).

Helper Methods

Several private methods are also defined to support the main functionality:

-   `_validate_request`: Validates the request to disable a rule.
-   `_fetch_filename`: Fetches the filename from the Wazuh-Manager that contains the rule to be disabled.
-   `_fetch_file_content`: Fetches the content of the file that contains the rule to be disabled.
-   `_set_level_1`: Sets the level of the rule to 1.
-   `_convert_to_xml`: Converts the updated file content to XML format.
-   `_store_disabled_rule_info`: Stores information about the disabled rule in the database.
-   `_upload_updated_rule`: Uploads the updated rule to the Wazuh Manager.

Error Handling

The script includes error handling using try/except blocks. When an error occurs, the error message is logged using loguru's `logger.error` function, and a dictionary with a failure message and success status set to False is returned.

The `WazuhHttpRequests` and `DisableRuleService` classes appear to be well-structured and follow good practices for encapsulating functionality related to Wazuh's rules system. Each class and method is well-documented with a docstring that describes its purpose, the arguments it accepts (if any), and what it returns.

::: app.services.WazuhManager.disabled_rule

### <span style="color:red">Wazuh-Manager Services Enabled Rule</span>

## enabled_rule.py Markdown Explanation

The `enabled_rule.py` file appears to be a Python module that defines two classes: `WazuhHttpRequests` and `EnableRuleService`. These classes encapsulate the functionality for interacting with the Wazuh Manager rules system, specifically for enabling rules.

### Imports

The script imports necessary modules at the beginning:

-   `requests`: A popular Python library used for making HTTP requests.
-   `loguru`: A third-party library providing a more convenient and powerful logger for Python.
-   `typing`: A standard Python library for support of type hints.
-   `xmltodict`: A Python module that makes working with XML feel like you are working with JSON.
-   `app.models.rules.DisabledRules`: The `DisabledRules` class from the `app.models.rules` module.
-   `app.services.WazuhManager.universal.UniversalService`: The `UniversalService` class from the `app.services.WazuhManager.universal` module.

### Class Definition: WazuhHttpRequests

The `WazuhHttpRequests` class handles HTTP requests to the Wazuh API. It is initialized with the URL for the Wazuh connector and an authentication token. It provides methods to make HTTP GET and PUT requests to the specified Wazuh API endpoint.

### Class Definition: EnableRuleService

The `EnableRuleService` class encapsulates the logic for handling rule-enabling operations in the Wazuh Manager. It uses the `UniversalService` to get authentication tokens and URLs, and `WazuhHttpRequests` to make HTTP requests.

It provides a method to enable a specific rule in the Wazuh Manager (`enable_rule` method).

Helper Methods

Several private methods are also defined to support the main functionality:

-   `_validate_request`: Validates the request to enable a rule.
-   `_fetch_filename`: Fetches the filename from the Wazuh-Manager that contains the rule to be enabled.
-   `_fetch_file_content`: Fetches the content of the file that contains the rule to be enabled.
-   `_get_previous_level`: Fetches the previous level of a rule from the `disabled_rules` table.
-   `_set_level_previous`: Sets the level of the rule to its previous level in the file content.
-   `_json_to_xml`: Converts the updated file content to XML format.
-   `_delete_rule_from_db`: Deletes a rule from the `disabled_rules` table.
-   `_put_updated_rule`: Uploads the updated rule to the Wazuh Manager.

Error Handling

The script includes error handling using try/except blocks. When an error occurs, the error message is logged using loguru's `logger.error` function, and a dictionary with a failure message and success status set to False is returned.

The `WazuhHttpRequests` and `EnableRuleService` classes appear to be well-structured and follow good practices for encapsulating functionality related to Wazuh's rules system. Each class and method is well-documented with a docstring that describes its purpose, the arguments it accepts (if any), and what it returns.

::: app.services.WazuhManager.enabled_rule

### <span style="color:red">Wazuh-Manager Services Universal</span>

::: app.services.WazuhManager.universal

### <span style="color:red">Wazuh-Manager Services Vulnerability</span>

## vulnerability.py Markdown Explanation

The `vulnerability.py` file appears to be a Python module that defines two classes: `WazuhHttpRequests` and `VulnerabilityService`. These classes encapsulate the functionality for interacting with the Wazuh Manager's vulnerability system.

### Imports

The script imports necessary modules at the beginning:

-   `requests`: A popular Python library used for making HTTP requests.
-   `loguru`: A third-party library providing a more convenient and powerful logger for Python.
-   `typing`: A standard Python library for support of type hints.
-   `app.services.WazuhManager.universal.UniversalService`: The `UniversalService` class from the `app.services.WazuhManager.universal` module.

### Class Definition: WazuhHttpRequests

The `WazuhHttpRequests` class handles HTTP requests to the Wazuh API. It is initialized with the URL for the Wazuh connector and an authentication token. It provides a method to make HTTP GET requests to the specified Wazuh API endpoint.

### Class Definition: VulnerabilityService

The `VulnerabilityService` class encapsulates the logic for handling vulnerability-related operations in the Wazuh Manager. It uses the `UniversalService` to get authentication tokens and URLs, and `WazuhHttpRequests` to make HTTP requests.

It provides a method to retrieve and process vulnerabilities for a specified agent (`agent_vulnerabilities` method).

Helper Method

A private method is also defined to support the main functionality:

-   `_process_agent_vulnerabilities`: Processes the raw vulnerabilities data for an agent.

Error Handling

The script includes error handling using try/except blocks. When an error occurs, the error message is logged using loguru's `logger.error` function.

The `WazuhHttpRequests` and `VulnerabilityService` classes appear to be well-structured and follow good practices for encapsulating functionality related to Wazuh's vulnerability system. Each class and method is well-documented with a docstring that describes its purpose, the arguments it accepts (if any), and what it returns.

::: app.services.WazuhManager.vulnerability
