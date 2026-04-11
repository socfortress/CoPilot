import activeResponse from "./endpoints/activeResponse"
import agents from "./endpoints/agents"
import aiAnalyst from "./endpoints/aiAnalyst"
import alerts from "./endpoints/alerts"
import artifacts from "./endpoints/artifacts"
import askSocfortress from "./endpoints/askSocfortress"
import auth from "./endpoints/auth"
import cloudSecurityAssessment from "./endpoints/cloudSecurityAssessment"
import connectors from "./endpoints/connectors"
import copilotAction from "./endpoints/copilotAction"
import copilotMCP from "./endpoints/copilotMCP"
import copilotSearches from "./endpoints/copilotSearches"
import customerPortal from "./endpoints/customerPortal"
import customers from "./endpoints/customers"
import flow from "./endpoints/flow"
import githubAudit from "./endpoints/githubAudit"
import graylog from "./endpoints/graylog"
import healthchecks from "./endpoints/healthchecks"
import incidentManagement from "./endpoints/incidentManagement"
import integrations from "./endpoints/integrations"
import license from "./endpoints/license"
import logs from "./endpoints/logs"
import metrics from "./endpoints/metrics"
import monitoringAlerts from "./endpoints/monitoringAlerts"
import networkConnectors from "./endpoints/networkConnectors"
import patchTuesday from "./endpoints/patchTuesday"
import portainer from "./endpoints/portainer"
import reporting from "./endpoints/reporting"
import sca from "./endpoints/sca"
import scheduler from "./endpoints/scheduler"
import shuffle from "./endpoints/shuffle"
import siem from "./endpoints/siem"
import sigma from "./endpoints/sigma"
import snapshots from "./endpoints/snapshots"
import soc from "./endpoints/soc"
import sso from "./endpoints/sso"
import stackProvisioning from "./endpoints/stackProvisioning"
import sysmonConfig from "./endpoints/sysmonConfig"
import tagRbac from "./endpoints/tagRbac"
import talon from "./endpoints/talon"
import threatIntel from "./endpoints/threatIntel"
import totp from "./endpoints/totp"
import users from "./endpoints/users"
import version from "./endpoints/version"
import vulnerabilities from "./endpoints/vulnerabilities"
import wazuh from "./endpoints/wazuh"
import indices from "./endpoints/wazuh/indices"
import webVulnerabilityAssessment from "./endpoints/webVulnerabilityAssessment"

export default {
	agents,
	aiAnalyst,
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
	metrics,
	flow,
	integrations,
	monitoringAlerts,
	activeResponse,
	stackProvisioning,
	reporting,
	license,
	githubAudit,
	scheduler,
	networkConnectors,
	copilotSearches,
	cloudSecurityAssessment,
	webVulnerabilityAssessment,
	incidentManagement,
	sigma,
	users,
	sysmonConfig,
	vulnerabilities,
	sca,
	siem,
	wazuh,
	patchTuesday,
	portainer,
	shuffle,
	copilotMCP,
	customerPortal,
	version,
	snapshots,
	tagRbac,
	talon,
	sso,
	totp
}
