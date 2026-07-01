import activeResponse from "./endpoints/active-response"
import agents from "./endpoints/agents"
import aiAnalyst from "./endpoints/ai-analyst"
import alerts from "./endpoints/alerts"
import artifacts from "./endpoints/artifacts"
import askSocfortress from "./endpoints/ask-socfortress"
import audit from "./endpoints/audit"
import auth from "./endpoints/auth"
import cloudSecurityAssessment from "./endpoints/cloud-security-assessment"
import connectors from "./endpoints/connectors"
import copilotAction from "./endpoints/copilot-action"
import copilotMCP from "./endpoints/copilot-mcp"
import copilotSearches from "./endpoints/copilot-searches"
import customerPortal from "./endpoints/customer-portal"
import customers from "./endpoints/customers"
import detectionCatalog from "./endpoints/detection-catalog"
import flow from "./endpoints/flow"
import githubAudit from "./endpoints/github-audit"
import graylog from "./endpoints/graylog"
import healthchecks from "./endpoints/healthchecks"
import incidentManagement from "./endpoints/incidentManagement"
import integrations from "./endpoints/integrations"
import license from "./endpoints/license"
import logs from "./endpoints/logs"
import metrics from "./endpoints/metrics"
import monitoringAlerts from "./endpoints/monitoring-alerts"
import networkConnectors from "./endpoints/network-connectors"
import notifications from "./endpoints/notifications"
import passkey from "./endpoints/passkey"
import patchTuesday from "./endpoints/patch-tuesday"
import portainer from "./endpoints/portainer"
import reporting from "./endpoints/reporting"
import sca from "./endpoints/sca"
import scheduler from "./endpoints/scheduler"
import shuffle from "./endpoints/shuffle"
import sidebarContext from "./endpoints/sidebar-context"
import siem from "./endpoints/siem"
import sigma from "./endpoints/sigma"
import snapshots from "./endpoints/snapshots"
import soc from "./endpoints/soc"
import sso from "./endpoints/sso"
import stackProvisioning from "./endpoints/stack-provisioning"
import sysmonConfig from "./endpoints/sysmon-config"
import tagRbac from "./endpoints/tag-rbac"
import talon from "./endpoints/talon"
import threatIntel from "./endpoints/threat-intel"
import totp from "./endpoints/totp"
import users from "./endpoints/users"
import version from "./endpoints/version"
import vulnerabilities from "./endpoints/vulnerabilities"
import wazuh from "./endpoints/wazuh"
import indices from "./endpoints/wazuh/indices"
import webVulnerabilityAssessment from "./endpoints/web-vulnerability-assessment"

export default {
	agents,
	aiAnalyst,
	alerts,
	artifacts,
	auth,
	audit,
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
	notifications,
	copilotSearches,
	detectionCatalog,
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
	sidebarContext,
	snapshots,
	tagRbac,
	talon,
	sso,
	totp,
	passkey
}
