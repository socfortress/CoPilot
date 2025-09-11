import activeResponse from "./endpoints/activeResponse"
import agents from "./endpoints/agents"
import alerts from "./endpoints/alerts"
import artifacts from "./endpoints/artifacts"
import askSocfortress from "./endpoints/askSocfortress"
import auth from "./endpoints/auth"
import cloudSecurityAssessment from "./endpoints/cloudSecurityAssessment"
import connectors from "./endpoints/connectors"
import copilotAction from "./endpoints/copilotAction"
import copilotMCP from "./endpoints/copilotMCP"
import customers from "./endpoints/customers"
import flow from "./endpoints/flow"
import graylog from "./endpoints/graylog"
import healthchecks from "./endpoints/healthchecks"
import incidentManagement from "./endpoints/incidentManagement"
import integrations from "./endpoints/integrations"
import license from "./endpoints/license"
import logs from "./endpoints/logs"
import monitoringAlerts from "./endpoints/monitoringAlerts"
import networkConnectors from "./endpoints/networkConnectors"
import portainer from "./endpoints/portainer"
import reporting from "./endpoints/reporting"
import sca from "./endpoints/sca"
import scheduler from "./endpoints/scheduler"
import shuffle from "./endpoints/shuffle"
import sigma from "./endpoints/sigma"
import soc from "./endpoints/soc"
import stackProvisioning from "./endpoints/stackProvisioning"
import sysmonConfig from "./endpoints/sysmonConfig"
import threatIntel from "./endpoints/threatIntel"
import users from "./endpoints/users"
import vulnerabilities from "./endpoints/vulnerabilities"
import wazuh from "./endpoints/wazuh"
import indices from "./endpoints/wazuh/indices"
import webVulnerabilityAssessment from "./endpoints/webVulnerabilityAssessment"

export default {
	agents,
	alerts,
	artifacts,
	auth,
	connectors,
	copilotAction,
	graylog,
	indices,
	soc,
	healthchecks,
	threatIntel,
	askSocfortress,
	customers,
	logs,
	flow,
	integrations,
	monitoringAlerts,
	activeResponse,
	stackProvisioning,
	reporting,
	license,
	scheduler,
	networkConnectors,
	cloudSecurityAssessment,
	webVulnerabilityAssessment,
	incidentManagement,
	sigma,
	users,
	sysmonConfig,
	vulnerabilities,
	sca,
	wazuh,
	portainer,
	shuffle,
	copilotMCP
}
