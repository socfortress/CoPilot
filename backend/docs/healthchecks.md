## Healthchecks Overview

### <span style="color:green">Healthchecks Routes</span>

# Healthchecks Module

The `healthchecks.py` module provides a set of HTTP endpoints for checking the health status of different agents in the system.

## Endpoints

### GET /healthcheck/agent/full

This endpoint retrieves a list of all agents who have sent logs within the last 15 minutes. It also returns a list of agents who haven't sent logs within the same timeframe.

#### Response

A JSON response containing the list of all available agents along with their log existence status.

---

### GET /healthcheck/agent/{agent_id}/full

This endpoint retrieves the log existence status of a specific agent.

#### Parameters

-   `agent_id`: The ID of the agent.

#### Response

A JSON response containing the log existence status of the agent.

---

### GET /healthcheck/agent/wazuh

This endpoint retrieves a list of all agents whose Wazuh-Agent is running. It also returns a list of agents whose Wazuh-Agent is not running.

#### Response

A JSON response containing the list of all available agents along with their Wazuh-Agent status.

---

### GET /healthcheck/agent/{agent_id}/wazuh

This endpoint retrieves the Wazuh-Agent status of a specific agent.

#### Parameters

-   `agent_id`: The ID of the agent.

#### Response

A JSON response containing the Wazuh-Agent status of the agent.

---

### GET /healthcheck/agent/velociraptor

This endpoint retrieves a list of all agents whose Velociraptor service is running. It also returns a list of agents whose Velociraptor service is not running.

#### Response

A JSON response containing the list of all available agents along with their Velociraptor service status.

---

### GET /healthcheck/agent/{agent_id}/velociraptor

This endpoint retrieves the Velociraptor service status of a specific agent.

#### Parameters

-   `agent_id`: The ID of the agent.

#### Response

A JSON response containing the Velociraptor service status of the agent.

::: app.routes.healthchecks
<br>

### <span style="color:red">Healthcheck Agent Services</span>

# HealthcheckAgentsService Class

The `HealthcheckAgentsService` class encapsulates the logic for CoPilot healthchecks. It provides several methods to perform healthchecks and related operations.

## Methods

### `__init__`

The initializer method of the class. It initializes an instance of the `UniversalService` class.

---

### `convert_string_to_datetime(date_string: str) -> datetime`

This method converts a string into a datetime object.

#### Parameters

-   `date_string`: The date string to be converted.

#### Returns

-   The converted datetime object.

---

### `is_agent_unhealthy(agent: Dict, current_time: datetime) -> bool`

This method determines if an agent is unhealthy based on the last seen time of the agent and the current time.

#### Parameters

-   `agent`: The agent data.
-   `current_time`: The current time.

#### Returns

-   A boolean indicating if the agent is unhealthy.

---

### `get_indices() -> List[str]`

This method returns a list of all indices in the Wazuh-Indexer.

#### Returns

-   A list of all indices.

---

### `has_agent_recent_logs(agent: Dict, indices: List[str]) -> bool`

This method checks if an agent has recent logs.

#### Parameters

-   `agent`: The agent data.
-   `indices`: The indices to be checked.

#### Returns

-   A boolean indicating if the agent has recent logs.

---

### `perform_healthcheck_full(agents: List[Dict], check_logs: bool = False) -> Dict`

This method performs a full healthcheck on all agents.

#### Parameters

-   `agents`: A list of all agents.
-   `check_logs`: Whether to check if agents have recent logs.

#### Returns

-   A dictionary containing the healthcheck results for all agents.

---

### `perform_healthcheck_wazuh(agents: Union[List[Dict], Dict]) -> Dict`

This method checks the health of Wazuh agents.

#### Parameters

-   `agents`: Either a list of agents or a single agent.

#### Returns

-   A dictionary containing the healthcheck results for Wazuh agents.

---

### `perform_healthcheck_velociraptor(agents: Union[List[Dict], Dict]) -> Dict`

This method checks the health of Velociraptor clients.

#### Parameters

-   `agents`: Either a list of agents or a single agent.

#### Returns

-   A dictionary containing the healthcheck results for Velociraptor clients.

::: app.services.Healthchecks.agents
<br>
