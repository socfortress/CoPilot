import type { VueWrapper } from "@vue/test-utils"
import type { Router } from "vue-router"
import { flushPromises } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { mountWithRouter } from "@/components/common/__tests__/modal-page-harness"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import PatchTuesdayCard from "@/components/patchTuesday/PatchTuesdayCard.vue"
import ScaCard from "@/components/sca/ScaCard.vue"
import PolicyCard from "@/components/scaPolicies/PolicyCard.vue"
import VulnerabilityOverviewCard from "@/components/vulnerabilities/VulnerabilityCard.vue"
import AgentArtifactCard from "../dataStore/AgentArtifactCard.vue"
import ScaResultItem from "../sca/ScaResultItem.vue"
import ScaTable from "../sca/ScaTable.vue"
import AgentVulnerabilityCard from "../vulnerabilities/VulnerabilityCard.vue"

/**
 * Entity modals and drawers of agents, vulnerabilities, SCA and Patch Tuesday offer the
 * entity's own page from their header: the link points at the real route, and following
 * it closes the overlay.
 */

const getSCA = vi.fn()
vi.mock("@/api", async () => {
	const { pendingApi } = await import("@/components/common/__tests__/modal-page-stubs")
	return { default: pendingApi({ agents: { getSCA: (...args: unknown[]) => getSCA(...args) } }) }
})
vi.mock("naive-ui", async importOriginal => {
	const { stubOverlays } = await import("@/components/common/__tests__/modal-page-stubs")
	return stubOverlays(await importOriginal<Record<string, unknown>>())
})

async function open(wrapper: VueWrapper) {
	wrapper.findComponent(EntityDetailsButton).vm.$emit("view")
	await flushPromises()
}

/** The overlay is open, links `href`, and following the link closes it on that page. */
async function expectPageLink(wrapper: VueWrapper, router: Router, href: string, label: string) {
	// The overlay that holds the page button (a card may own other overlays).
	const holder = wrapper
		.findAll("[data-testid=overlay-stub]")
		.find(candidate => candidate.find("[data-testid=modal-page-button]").exists())
	expect(holder, "no overlay carries a page button").toBeTruthy()
	const overlay = () => holder?.attributes("data-show")
	expect(overlay()).toBe("true")
	const link = wrapper.get("[data-testid=modal-page-button]")
	expect(link.attributes("href")).toBe(href)
	expect(link.attributes("aria-label")).toBe(label)
	await link.trigger("click", { button: 0 })
	await flushPromises()
	expect(overlay()).toBe("false")
	expect(router.currentRoute.value.fullPath).toBe(href)
}

describe("agent entity modals", () => {
	it("artifact → its data-store page", async () => {
		const artifact = { id: 9, artifact_name: "Windows.KapeFiles", file_name: "a.zip", file_size: 10, status: "done" }
		const { wrapper, router } = await mountWithRouter(
			AgentArtifactCard,
			{ artifact, agentId: "007", showActions: true },
			["ArtifactDetails"]
		)
		await open(wrapper)
		await expectPageLink(wrapper, router, "/agents/007/data-store/9", "Open the artifact's page")
	})

	it("sCA check → its check page", async () => {
		const data = { id: 31, policy_id: "cis_win", title: "Ensure X", result: "failed", compliance: [], rules: [] }
		const { wrapper, router } = await mountWithRouter(ScaResultItem, { data, agentId: "007" }, ["ScaResultItemDetails"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/agents/007/sca/cis_win/checks/31", "Open the check's page")
	})

	it("sCA check without an owner agent has no page to offer", async () => {
		const data = { id: 31, policy_id: "cis_win", title: "Ensure X", result: "failed", compliance: [], rules: [] }
		const { wrapper } = await mountWithRouter(ScaResultItem, { data }, ["ScaResultItemDetails"])
		await open(wrapper)
		expect(wrapper.find("[data-testid=modal-page-button]").exists()).toBe(false)
	})

	it("agent SCA policy (table row) → the agent's policy page", async () => {
		getSCA.mockResolvedValue({
			data: { success: true, sca: [{ policy_id: "cis_win", name: "CIS Windows", description: "d", end_scan: null }] }
		})
		const { wrapper, router } = await mountWithRouter(ScaTable, { agent: { agent_id: "007" } }, ["ScaItem"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/agents/007/sca/cis_win", "Open the policy's page")
	})

	it("agent vulnerability → its page, disambiguated by package", async () => {
		const vulnerability = { cve: "CVE-2026-1", name: "openssl", version: "3.0", severity: "High", value: {} }
		const { wrapper, router } = await mountWithRouter(AgentVulnerabilityCard, { vulnerability, agentId: "007" }, [
			"VulnerabilityDetails"
		])
		await open(wrapper)
		await expectPageLink(
			wrapper,
			router,
			"/agents/007/vulnerabilities/CVE-2026-1?package=openssl&version=3.0",
			"Open the vulnerability's page"
		)
	})
})

describe("overview entity modals", () => {
	it("vulnerability overview → its agent + CVE page", async () => {
		const vulnerability = {
			cve_id: "CVE-2026-2",
			agent_name: "host-1",
			package_name: "curl",
			package_version: "8.0",
			severity: "Critical",
			title: "curl",
			detected_at: "2026-09-01T00:00:00"
		}
		const { wrapper, router } = await mountWithRouter(VulnerabilityOverviewCard, { vulnerability }, [
			"VulnerabilityCardContent"
		])
		await open(wrapper)
		await expectPageLink(
			wrapper,
			router,
			"/agents/vulnerability-overview/host-1/CVE-2026-2?package=curl&version=8.0",
			"Open the vulnerability's page"
		)
	})

	it("sCA overview result → the agent's policy page", async () => {
		const sca = { agent_id: "007", agent_name: "host-1", policy_id: "cis_win", policy_name: "CIS", score: 70 }
		const { wrapper, router } = await mountWithRouter(ScaCard, { sca }, ["ScaCardContent"])
		// The whole card opens it.
		wrapper.findComponent({ name: "CardEntity" }).vm.$emit("click", new MouseEvent("click"))
		await flushPromises()
		await expectPageLink(wrapper, router, "/agents/007/sca/cis_win", "Open the policy's page")
	})

	it("sCA policy → its policy page", async () => {
		const policy = { id: "cis_win", name: "CIS Windows", description: "d", file: "cis.yml", platform: "windows" }
		const { wrapper, router } = await mountWithRouter(PolicyCard, { policy }, ["PolicyCardContent"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/agents/sca-policies/cis_win", "Open the policy's page")
	})

	it("patch Tuesday CVE (drawer) → its cycle + CVE page", async () => {
		const item = {
			cycle: "2026-09",
			cve: "CVE-2026-3",
			title: "Windows",
			severity: "Critical",
			affected: { product: "Windows 11", family: "Windows" },
			cvss: { base: 8.1 },
			epss: { score: 0.2, percentile: 0.9 },
			kev: { in_kev: false },
			prioritization: { priority: "P1" },
			remediation: { kbs: [] }
		}
		const { wrapper, router } = await mountWithRouter(PatchTuesdayCard, { item }, ["PatchTuesdayDetail"])
		await open(wrapper)
		await expectPageLink(wrapper, router, "/patch-tuesday/2026-09/CVE-2026-3?product=Windows+11", "Open the CVE's page")
	})
})
