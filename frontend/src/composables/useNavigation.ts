import type { RouteLocationRaw } from "vue-router"
import type { CustomerHealthcheckSource } from "@/types/customers"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"

/** A resolved application route, as returned by every `route*()` helper below. */
export interface EntityRoute {
	navigate: () => void
	replace: () => void
	valueOf: () => string
	toString: () => string
	/** Relative href — use for `<a>` targets so middle-click / open-in-new-tab work. */
	href: () => string
	/** Absolute URL — use only for copy-link / share UI. */
	fullUrl: () => string
}

/**
 * Reads a route path param as a string, ignoring repeated params.
 * Returns null when the param is absent or empty.
 */
export function useRouteParam(name: string) {
	const route = useRoute()

	return computed(() => {
		const raw = route.params[name]
		const value = Array.isArray(raw) ? raw[0] : raw
		return value ? String(value) : null
	})
}

/** Reads a route path param as an integer. Returns null when absent or not a whole number. */
export function useRouteIdParam(name: string) {
	const param = useRouteParam(name)

	return computed(() => {
		if (param.value === null) return null

		const parsed = Number.parseInt(param.value, 10)
		return Number.isSafeInteger(parsed) ? parsed : null
	})
}

export function useNavigation() {
	const router = useRouter()

	function routerConstructor(route: RouteLocationRaw): EntityRoute {
		return {
			navigate: () => router.push(route),
			replace: () => router.replace(route),
			valueOf: () => router.resolve(route).href,
			toString: () => router.resolve(route).href,
			href: () => router.resolve(route).href,
			fullUrl: () => {
				const resolved = router.resolve(route)
				return `${window.location.protocol}//${window.location.host}${resolved.href}`
			}
		}
	}

	/** Returns to the previous page, falling back to the given route on a cold load (deep link). */
	function goBack(fallback?: EntityRoute) {
		if (window.history.length > 1) {
			router.back()
			return
		}

		fallback?.navigate()
	}

	function routeCustomer(params?: { code?: string | number; action?: "add-customer" }) {
		if (params?.code) {
			return routerConstructor({
				name: "Customer",
				params: { code: params.code.toString() }
			})
		} else if (params?.action) {
			return routerConstructor({ name: "Customers", query: { action: params.action.toString() } })
		} else {
			return routerConstructor({ name: "Customers" })
		}
	}

	function routeCustomerHealthcheckAgent(
		customerCode?: string,
		source?: CustomerHealthcheckSource,
		agentId?: string
	) {
		if (customerCode && source && agentId) {
			return routerConstructor({
				name: "CustomerHealthcheckAgent",
				params: { code: customerCode, source, agentId }
			})
		}

		if (customerCode) {
			return routerConstructor({ name: "Customer", params: { code: customerCode } })
		}

		return routerConstructor({ name: "Customers" })
	}

	function routeAgent(agentId?: string | number) {
		if (agentId) {
			return routerConstructor({ name: "Agent", params: { id: agentId.toString() } })
		} else {
			return routerConstructor({ name: "Agents" })
		}
	}

	function routeIndex(indexName?: string) {
		return routerConstructor({ name: "Indices", query: indexName ? { index_name: indexName } : {} })
	}

	function routeLicense() {
		return routerConstructor({ name: "License" })
	}

	function routeHealthcheck() {
		return routerConstructor({ name: "Healthcheck" })
	}

	function routeMetrics() {
		return routerConstructor({ name: "Metrics" })
	}

	function routeGraylogMetrics() {
		return routerConstructor({ name: "Graylog-Metrics" })
	}

	function routeDashboard(dashboardId?: number | string) {
		if (dashboardId != null) {
			return routerConstructor({
				name: "DashboardView",
				params: { id: dashboardId.toString() }
			})
		}

		return routerConstructor({ name: "Dashboards" })
	}

	function routeGraylogManagement(
		tabName?: "messages" | "alerts" | "events" | "streams" | "provisioning" | "inputs"
	) {
		return routerConstructor({ name: "Graylog-Management", hash: tabName ? `#${tabName}` : undefined })
	}

	function routeSocAlerts() {
		return routerConstructor({ name: "Soc-Alerts" })
	}

	function routeAlerts() {
		return routerConstructor({ name: "Alerts" })
	}

	function routeAlertsSiemSummary(
		indexName?: string,
		query?: Partial<{ size: number; timerange: string; index_prefix: string }>
	) {
		if (indexName) {
			return routerConstructor({
				name: "Alerts-SIEM-Summary",
				params: { indexName },
				query: query ?? {}
			})
		}

		return routerConstructor({ name: "Alerts-SIEM" })
	}

	function routeAlertsSiemAlert(indexName?: string, alertId?: string) {
		if (indexName && alertId) {
			return routerConstructor({
				name: "Alerts-SIEM-Alert",
				params: { indexName, alertId }
			})
		}

		return routerConstructor({ name: "Alerts-SIEM" })
	}

	function routeAlertsMitre() {
		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreTechnique(techniqueId?: string) {
		if (techniqueId) {
			return routerConstructor({
				name: "Alerts-Mitre-Technique",
				params: { techniqueId }
			})
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreTechniques(techniqueId?: string) {
		if (techniqueId) {
			return routerConstructor({
				name: "Alerts-Mitre-Techniques",
				params: { techniqueId }
			})
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreEvent(techniqueId?: string, eventId?: string) {
		if (techniqueId && eventId) {
			return routerConstructor({
				name: "Alerts-Mitre-Technique-Event",
				params: { techniqueId, eventId }
			})
		}

		if (techniqueId) {
			return routeAlertsMitreTechnique(techniqueId)
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreGroup(groupId?: string) {
		if (groupId) {
			return routerConstructor({
				name: "Alerts-Mitre-Group",
				params: { groupId }
			})
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreMitigation(mitigationId?: string) {
		if (mitigationId) {
			return routerConstructor({
				name: "Alerts-Mitre-Mitigation",
				params: { mitigationId }
			})
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreSoftware(softwareId?: string) {
		if (softwareId) {
			return routerConstructor({
				name: "Alerts-Mitre-Software",
				params: { softwareId }
			})
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsMitreTactic(tacticId?: string) {
		if (tacticId) {
			return routerConstructor({
				name: "Alerts-Mitre-Tactic",
				params: { tacticId }
			})
		}

		return routerConstructor({ name: "Alerts-Mitre" })
	}

	function routeAlertsAtomicRedTeam() {
		return routerConstructor({ name: "Alerts-AtomicRedTeam" })
	}

	function routeAlertsAtomicRedTeamTechnique(techniqueId?: string) {
		if (techniqueId) {
			return routerConstructor({
				name: "Alerts-AtomicRedTeam-Technique",
				params: { techniqueId }
			})
		}

		return routerConstructor({ name: "Alerts-AtomicRedTeam" })
	}

	function routeConnectors() {
		return routerConstructor({ name: "Connectors" })
	}

	function routeGraylogPipelines(rule?: string) {
		return routerConstructor({ name: "Graylog-Pipelines", query: rule ? { rule } : {} })
	}

	function routeSocUsers(userId?: string | number) {
		return routerConstructor({ name: "Soc-Users", query: userId ? { user_id: userId } : {} })
	}

	function routeIncidentManagementAlerts(alertId?: number) {
		if (alertId != null) {
			return routerConstructor({
				name: "IncidentManagement-Alert",
				params: { id: alertId.toString() }
			})
		}

		return routerConstructor({ name: "IncidentManagement-Alerts" })
	}

	function routeIncidentManagementAlertAsset(alertId?: number, assetId?: number) {
		if (alertId != null && assetId != null) {
			return routerConstructor({
				name: "IncidentManagement-AlertAsset",
				params: { alertId: alertId.toString(), assetId: assetId.toString() }
			})
		}

		if (alertId != null) {
			return routeIncidentManagementAlerts(alertId)
		}

		return routerConstructor({ name: "IncidentManagement-Alerts" })
	}

	function routeIncidentManagementAlertIoc(alertId?: number, iocId?: number) {
		if (alertId != null && iocId != null) {
			return routerConstructor({
				name: "IncidentManagement-AlertIoc",
				params: { alertId: alertId.toString(), iocId: iocId.toString() }
			})
		}

		if (alertId != null) {
			return routeIncidentManagementAlerts(alertId)
		}

		return routerConstructor({ name: "IncidentManagement-Alerts" })
	}

	function routeIncidentManagementAlertIocNew(alertId?: number) {
		if (alertId != null) {
			return routerConstructor({
				name: "IncidentManagement-AlertIocNew",
				params: { alertId: alertId.toString() }
			})
		}

		return routerConstructor({ name: "IncidentManagement-Alerts" })
	}

	function routeIncidentManagementCases(caseId?: number) {
		if (caseId != null) {
			return routerConstructor({
				name: "IncidentManagement-Case",
				params: { id: caseId.toString() }
			})
		}

		return routerConstructor({ name: "IncidentManagement-Cases" })
	}

	function routeIncidentManagementSources() {
		return routerConstructor({ name: "IncidentManagement-Sources" })
	}

	function routeIncidentManagementExclusionRuleNew() {
		return routerConstructor({ name: "IncidentManagement-ExclusionRuleNew" })
	}

	function routeIncidentManagementExclusionRule(exclusionId?: number) {
		if (exclusionId != null) {
			return routerConstructor({
				name: "IncidentManagement-ExclusionRule",
				params: { id: exclusionId.toString() }
			})
		}

		return routerConstructor({ name: "IncidentManagement-Sources" })
	}

	function routeIncidentManagementSourceNew() {
		return routerConstructor({ name: "IncidentManagement-SourceNew" })
	}

	function routeIncidentManagementSource(source?: string) {
		if (source) {
			return routerConstructor({
				name: "IncidentManagement-Source",
				params: { source }
			})
		}

		return routerConstructor({ name: "IncidentManagement-Sources" })
	}

	function routeEventSearch(params?: { customer_code?: string; source_name?: string; query?: string }) {
		const routeQuery: Record<string, string> = {}
		if (params?.customer_code) routeQuery.customer_code = params.customer_code
		if (params?.source_name) routeQuery.source_name = params.source_name
		if (params?.query) routeQuery.query = params.query
		return routerConstructor({ name: "EventSearch", query: routeQuery })
	}

	function routeEventSearchEvent(customerCode?: string, sourceName?: string, indexName?: string, eventId?: string) {
		if (customerCode && sourceName && indexName && eventId) {
			// vue-router percent-encodes params on resolve and decodes them on read — do not pre-encode
			return routerConstructor({
				name: "EventSearch-Event",
				params: { customerCode, sourceName, indexName, eventId }
			})
		}

		return routerConstructor({ name: "EventSearch" })
	}

	function routeSSOConfig() {
		return routerConstructor({ name: "SSOConfig" })
	}

	function routeAudit(auditId?: number) {
		if (auditId != null) {
			return routerConstructor({
				name: "AuditEntry",
				params: { id: auditId.toString() }
			})
		}

		return routerConstructor({ name: "Audit" })
	}

	function routeThirdPartyIntegration(integrationId?: number) {
		if (integrationId != null) {
			return routerConstructor({
				name: "ExternalServices-ThirdPartyIntegration",
				params: { id: integrationId.toString() }
			})
		}

		return routerConstructor({ name: "ExternalServices-ThirdPartyIntegrations" })
	}

	function routeNetworkConnector(networkConnectorId?: number) {
		if (networkConnectorId != null) {
			return routerConstructor({
				name: "ExternalServices-NetworkConnector",
				params: { id: networkConnectorId.toString() }
			})
		}

		return routerConstructor({ name: "ExternalServices-NetworkConnectors" })
	}

	function routeSchedulerJob(jobId?: string) {
		if (jobId) {
			return routerConstructor({
				name: "SchedulerJob",
				params: { id: jobId }
			})
		}

		return routerConstructor({ name: "Scheduler" })
	}

	function routeUser(userId?: number) {
		if (userId != null) {
			return routerConstructor({
				name: "UserView",
				params: { id: userId.toString() }
			})
		}

		return routerConstructor({ name: "Users" })
	}

	function routeUserNew() {
		return routerConstructor({ name: "UserNew" })
	}

	function routeDetectionCatalogStory(storyName?: string) {
		if (storyName) {
			return routerConstructor({
				name: "DetectionCatalogStory",
				params: { name: storyName }
			})
		}

		return routerConstructor({ name: "DetectionCatalog" })
	}

	function routeDetectionCatalogDetection(detectionId?: string) {
		if (detectionId) {
			return routerConstructor({
				name: "DetectionCatalogDetection",
				params: { id: detectionId }
			})
		}

		return routerConstructor({ name: "DetectionCatalog" })
	}

	function routeDetectionCatalogCoverageGap(techniqueId?: string) {
		if (techniqueId) {
			return routerConstructor({
				name: "DetectionCatalogCoverageGap",
				params: { techniqueId }
			})
		}

		return routerConstructor({ name: "DetectionCatalog" })
	}

	function routeDetectionCatalogComplianceGroup(framework?: string, control?: string) {
		if (framework && control) {
			return routerConstructor({
				name: "DetectionCatalogComplianceGroup",
				params: { framework, control }
			})
		}

		return routerConstructor({ name: "DetectionCatalog" })
	}

	function routeDetectionCatalogWazuhRule(ruleId?: number) {
		if (ruleId != null) {
			return routerConstructor({
				name: "DetectionCatalogWazuhRule",
				params: { id: ruleId.toString() }
			})
		}

		return routerConstructor({ name: "DetectionCatalog" })
	}

	function routeAiAnalystJob(jobId?: string) {
		if (jobId) {
			return routerConstructor({
				name: "AiAnalystJob",
				params: { id: jobId }
			})
		}

		return routerConstructor({ name: "AiAnalyst" })
	}

	function routeAiAnalystIoc(iocId?: number) {
		if (iocId != null) {
			return routerConstructor({
				name: "AiAnalystIoc",
				params: { id: iocId.toString() }
			})
		}

		return routerConstructor({ name: "AiAnalyst" })
	}

	function routeAiAnalystFeedbackReview(reviewId?: number) {
		if (reviewId != null) {
			return routerConstructor({
				name: "AiAnalystFeedbackReview",
				params: { id: reviewId.toString() }
			})
		}

		return routerConstructor({ name: "AiAnalyst" })
	}

	function routeAiAnalystReport(reportId?: number) {
		if (reportId != null) {
			return routerConstructor({
				name: "AiAnalystReport",
				params: { id: reportId.toString() }
			})
		}

		return routerConstructor({ name: "AiAnalyst" })
	}

	return {
		goBack,
		routeCustomer,
		routeCustomerHealthcheckAgent,
		routeAgent,
		routeIndex,
		routeLicense,
		routeHealthcheck,
		routeMetrics,
		routeGraylogMetrics,
		routeDashboard,
		routeGraylogManagement,
		routeSocAlerts,
		routeGraylogPipelines,
		routeSocUsers,
		routeAlerts,
		routeAlertsSiemSummary,
		routeAlertsSiemAlert,
		routeAlertsMitre,
		routeAlertsMitreTechnique,
		routeAlertsMitreTechniques,
		routeAlertsMitreEvent,
		routeAlertsMitreGroup,
		routeAlertsMitreMitigation,
		routeAlertsMitreSoftware,
		routeAlertsMitreTactic,
		routeAlertsAtomicRedTeam,
		routeAlertsAtomicRedTeamTechnique,
		routeConnectors,
		routeIncidentManagementAlerts,
		routeIncidentManagementAlertAsset,
		routeIncidentManagementAlertIoc,
		routeIncidentManagementAlertIocNew,
		routeIncidentManagementCases,
		routeIncidentManagementSources,
		routeIncidentManagementExclusionRuleNew,
		routeIncidentManagementExclusionRule,
		routeIncidentManagementSourceNew,
		routeIncidentManagementSource,
		routeEventSearch,
		routeEventSearchEvent,
		routeSSOConfig,
		routeAudit,
		routeThirdPartyIntegration,
		routeNetworkConnector,
		routeSchedulerJob,
		routeUser,
		routeUserNew,
		routeDetectionCatalogStory,
		routeDetectionCatalogDetection,
		routeDetectionCatalogWazuhRule,
		routeDetectionCatalogCoverageGap,
		routeDetectionCatalogComplianceGroup,
		routeAiAnalystJob,
		routeAiAnalystIoc,
		routeAiAnalystFeedbackReview,
		routeAiAnalystReport
	}
}
