import activeResponse from "./endpoints/activeResponse"
import agents from "./endpoints/agents"
import alerts from "./endpoints/alerts"
import artifacts from "./endpoints/artifacts"
import askSocfortress from "./endpoints/askSocfortress"
import auth from "./endpoints/auth"
import cloudSecurityAssessment from "./endpoints/cloudSecurityAssessment"
import connectors from "./endpoints/connectors"
import customers from "./endpoints/customers"
import flow from "./endpoints/flow"
import graylog from "./endpoints/graylog"
import healthchecks from "./endpoints/healthchecks"
import incidentManagement from "./endpoints/incidentManagement"
import indices from "./endpoints/indices"
import integrations from "./endpoints/integrations"
import license from "./endpoints/license"
import logs from "./endpoints/logs"
import monitoringAlerts from "./endpoints/monitoringAlerts"
import networkConnectors from "./endpoints/networkConnectors"
import portainer from "./endpoints/portainer"
import reporting from "./endpoints/reporting"
import scheduler from "./endpoints/scheduler"
import sigma from "./endpoints/sigma"
import soc from "./endpoints/soc"
import stackProvisioning from "./endpoints/stackProvisioning"
import threatIntel from "./endpoints/threatIntel"
import users from "./endpoints/users"
import webVulnerabilityAssessment from "./endpoints/webVulnerabilityAssessment"

export default {
	agents,
	alerts,
	artifacts,
	auth,
	connectors,
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
	portainer
}
