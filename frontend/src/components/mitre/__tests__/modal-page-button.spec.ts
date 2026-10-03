import type { VueWrapper } from "@vue/test-utils"
import type { Router } from "vue-router"
import { flushPromises } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { mountWithRouter } from "@/components/common/__tests__/modal-page-harness"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import ActionCard from "@/components/copilotAction/ActionCard.vue"
import MatrixView from "@/components/copilotSearches/MatrixView/MatrixView.vue"
import RuleCard from "@/components/copilotSearches/RuleCard.vue"
import AtomicTechniqueCard from "../AtomicTests/TechniqueCard.vue"
import GroupCard from "../Group/GroupCard.vue"
import MitigationCard from "../Mitigation/MitigationCard.vue"
import SoftwareCard from "../Software/SoftwareCard.vue"
import TacticCard from "../Tactic/TacticCard.vue"
import TechniqueCard from "../Technique/TechniqueCard.vue"
import TechniqueAlertCard from "../TechniqueAlert/TechniqueAlertCard.vue"
import TechniqueEventCard from "../TechniqueEvents/TechniqueEventCard.vue"

/**
 * Entity modals of MITRE ATT&CK, Atomic Red Team, CoPilot Searches and CoPilot Actions
 * offer the entity's own page from their header: the link points at the real route, and
 * following it closes the modal.
 */

vi.mock("@/api", async () => {
	const { pendingApi } = await import("@/components/common/__tests__/modal-page-stubs")
	return { default: pendingApi() }
})
vi.mock("naive-ui", async importOriginal => {
	const { stubOverlays } = await import("@/components/common/__tests__/modal-page-stubs")
	return stubOverlays(await importOriginal<Record<string, unknown>>())
})

async function open(wrapper: VueWrapper) {
	wrapper.findComponent(EntityDetailsButton).vm.$emit("view")
	await flushPromises()
}

async function expectPageLink(wrapper: VueWrapper, router: Router, href: string, label: string) {
	const holder = wrapper
		.findAll("[data-testid=overlay-stub]")
		.find(candidate => candidate.find("[data-testid=modal-page-button]").exists())
	if (!holder) throw new Error("no overlay carries a page button")
	const overlay = () => holder.attributes("data-show")
	expect(overlay()).toBe("true")
	const link = holder.get("[data-testid=modal-page-button]")
	expect(link.attributes("href")).toBe(href)
	expect(link.attributes("aria-label")).toBe(label)
	await link.trigger("click", { button: 0 })
	await flushPromises()
	expect(overlay()).toBe("false")
	expect(router.currentRoute.value.fullPath).toBe(href)
}

describe("mITRE ATT&CK entity modals", () => {
	it.each([
		[GroupCard, "G0016", "GroupOverview", "/alerts/mitre/groups/G0016", "group"],
		[MitigationCard, "M1036", "MitigationOverview", "/alerts/mitre/mitigations/M1036", "mitigation"],
		[SoftwareCard, "S0002", "SoftwareOverview", "/alerts/mitre/software/S0002", "software"],
		[TacticCard, "TA0002", "TacticOverview", "/alerts/mitre/tactics/TA0002", "tactic"],
		[TechniqueCard, "T1059", "TechniqueOverview", "/alerts/mitre/techniques/T1059", "technique"]
	])("%o → its page", async (component, id, overview, href, entity) => {
		const { wrapper, router } = await mountWithRouter(component, { id }, [overview])
		await open(wrapper)
		await expectPageLink(wrapper, router, href, `Open the ${entity}'s page`)
	})

	it("technique with alerts → the technique's alerts page", async () => {
		const entity = { technique_id: "T1059", technique_name: "Command and Scripting Interpreter", count: 3 }
		const { wrapper, router } = await mountWithRouter(TechniqueAlertCard, { entity }, ["TechniqueAlertOverview"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/alerts/mitre/T1059", "Open the technique's page")
	})

	it("technique event → its event page", async () => {
		const alert = { id: "evt-1", agent_name: "host-1", rule_description: "r", timestamp_utc: "2026-09-01T00:00:00" }
		const { wrapper, router } = await mountWithRouter(TechniqueEventCard, { alert, techniqueId: "T1059" }, [
			"TechniqueEventOverview"
		])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/alerts/mitre/T1059/events/evt-1", "Open the alert's page")
	})

	it("atomic red team technique → its page", async () => {
		const entity = { technique_id: "T1059", technique_name: "Command and Scripting Interpreter", categories: [] }
		const { wrapper, router } = await mountWithRouter(AtomicTechniqueCard, { entity }, ["TechniqueCardContent"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/alerts/atomic-red-team/T1059", "Open the technique's page")
	})
})

describe("coPilot Actions and Searches entity modals", () => {
	it("action → its page (names keep their dots)", async () => {
		const action = {
			copilot_action_name: "Windows.Isolate.Host",
			description: "d",
			category: "Containment",
			technology: "Windows",
			version: "1.0",
			script_parameters: [],
			tags: []
		}
		const { wrapper, router } = await mountWithRouter(ActionCard, { action }, ["ActionCardContent", "InvokeActionForm"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/agents/copilot-actions/Windows.Isolate.Host", "Open the action's page")
	})

	it("detection rule card → the rule's page", async () => {
		const rule = { id: "rule-42", name: "Encoded PowerShell", mitre_attack_id: [], severity: "high", status: "production" }
		const { wrapper, router } = await mountWithRouter(RuleCard, { rule }, [
			"RuleCardContent",
			"ExecuteSearchForm",
			"ProvisionGraylogForm"
		])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/copilot-searches/rule-42", "Open the rule's page")
	})

	it("matrix quick rule modal → the rule's page, once a rule is open", async () => {
		const { wrapper, router } = await mountWithRouter(MatrixView, {}, [
			"MatrixViewToolbar",
			"MatrixViewLegend",
			"MatrixViewGrid",
			"TechniqueDetails",
			"RuleCardContent"
		])
		expect(wrapper.find("[data-testid=modal-page-button]").exists()).toBe(false)
		wrapper.findComponent({ name: "MatrixViewGrid" }).vm.$emit("open-rule", "rule-7")
		await flushPromises()
		await expectPageLink(wrapper, router, "/copilot-searches/rule-7", "Open the rule's page")
	})
})
