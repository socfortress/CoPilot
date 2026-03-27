import agents from "./endpoints/agents"
import alerts from "./endpoints/alerts"
import auth from "./endpoints/auth"
import celery from "./endpoints/celery"
import collectors from "./endpoints/collectors"
import customers from "./endpoints/customers"
import mcp from "./endpoints/mcp"
import monitoring from "./endpoints/monitoring"
import packages from "./endpoints/packages"
import ports from "./endpoints/ports"
import processes from "./endpoints/processes"
import tasks from "./endpoints/tasks"
import vulnerabilities from "./endpoints/vulnerabilities"
import websocket from "./endpoints/websocket"

export default {
	auth,
	agents,
	alerts,
	customers,
	packages,
	ports,
	processes,
	vulnerabilities,
	mcp,
	collectors,
	tasks,
	monitoring,
	celery,
	websocket
}
