import { describe, expect, it } from "vitest"

/**
 * Every modal (or drawer) that shows one entity which also has a page of its own offers
 * that page from its header, next to the close button (ModalPageButton). This list is
 * the inventory of those overlays: one that loses the button fails here, and a new
 * entity modal belongs on it. Forms, confirmations, wizards and entities without a page
 * (a customer's integration subscription, a timeline entry, a flow…) are deliberately
 * not on it.
 */
const ENTITY_OVERLAYS = [
	"components/agents/dataStore/AgentArtifactCard.vue",
	"components/agents/sca/ScaResultItem.vue",
	"components/agents/sca/ScaTable.vue",
	"components/agents/vulnerabilities/VulnerabilityCard.vue",
	"components/aiAnalyst/AlertReportItem.vue",
	"components/aiAnalyst/Feedback/FeedbackDashboardRecentReviews.vue",
	"components/alerts/Alert.vue",
	"components/copilotAction/ActionCard.vue",
	"components/copilotSearches/MatrixView/MatrixView.vue",
	"components/copilotSearches/RuleCard.vue",
	"components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteItem.vue",
	"components/customers/CustomerItem.vue",
	"components/customers/healthcheck/CustomerHealthcheckItem.vue",
	"components/detectionCatalog/ComplianceDetail.vue",
	"components/detectionCatalog/ComplianceIndex.vue",
	"components/detectionCatalog/CoverageGapsIndex.vue",
	"components/detectionCatalog/StoriesIndex.vue",
	"components/detectionCatalog/StoryDetail.vue",
	"components/detectionCatalog/WazuhRulesIndex.vue",
	"components/githubAudit/GitHubAuditCard.vue",
	"components/incidentManagement/alerts/AlertAsset.vue",
	"components/incidentManagement/alerts/AlertAssetInfo.vue",
	"components/incidentManagement/alerts/AlertItem.vue",
	"components/incidentManagement/cases/CaseItem.vue",
	"components/incidentManagement/exclusionRules/ExclusionRuleItem.vue",
	"components/incidentManagement/sources/ConfiguredSourceItem.vue",
	"components/mitre/AtomicTests/TechniqueCard.vue",
	"components/mitre/Group/GroupCard.vue",
	"components/mitre/Mitigation/MitigationCard.vue",
	"components/mitre/Software/SoftwareCard.vue",
	"components/mitre/Tactic/TacticCard.vue",
	"components/mitre/Technique/TechniqueCard.vue",
	"components/mitre/TechniqueAlert/TechniqueAlertCard.vue",
	"components/mitre/TechniqueEvents/TechniqueEventCard.vue",
	"components/notifications/NotificationTemplateItem.vue",
	"components/patchTuesday/PatchTuesdayCard.vue",
	"components/sca/ScaCard.vue",
	"components/scaPolicies/PolicyCard.vue",
	"components/services/Item.vue",
	"components/socManagement/EntityOverviewModal.vue",
	"components/vulnerabilities/VulnerabilityCard.vue"
]

const sources = import.meta.glob("/src/components/**/*.vue", { query: "?raw", import: "default", eager: true }) as Record<
	string,
	string
>

describe("entity modals link their page", () => {
	it.each(ENTITY_OVERLAYS)("%s puts ModalPageButton in its header", file => {
		const source = sources[`/src/${file}`]
		expect(source, `${file} not found`).toBeTypeOf("string")
		expect(source).toContain("<ModalPageButton")
		expect(source).toMatch(/#header(-extra)?/)
		expect(source).toMatch(/@navigate=/)
	})
})
