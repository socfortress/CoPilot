/**
 * The sidebar restructure (#1152) moved and renamed most entries. These pin
 * what must survive any future reshuffle:
 *
 * - every page the menu reached before still has an entry;
 * - every entry's key is the route its link opens, which is what Navbar.vue
 *   highlights the current page by;
 * - keys are unique (before #1152, "Agents" was both a section and a page);
 * - analysts keep every entry they had, minus the admin-only ones.
 */

import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import type { RouteRecordRaw } from "vue-router"
import { describe, expect, it, vi } from "vitest"
import { routes } from "@/router/routes"
import getItems from "../items"
import { ACTIVE_RESPONSE_PANEL_KEY } from "../items/respond"

const auth = { isAdmin: true }

vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))

const PANEL_KEYS = [ACTIVE_RESPONSE_PANEL_KEY]

/** Every destination the sidebar and the avatar menu reached before #1152. */
const PREVIOUS_DESTINATIONS = [
	"Overview",
	"AiAnalyst",
	"DetectionCatalog",
	"Customers",
	"InternalNotifications",
	"MessageTemplates",
	"Alerts-SIEM",
	"EventSearch",
	"Dashboards",
	"Alerts-Mitre",
	"Alerts-AtomicRedTeam",
	"IncidentManagement-Sources",
	"IncidentManagement-Alerts",
	"IncidentManagement-Cases",
	"IncidentManagement-CaseTemplates",
	"Agents",
	"Artifacts",
	"Groups",
	"SysmonConfig",
	"DetectionRules",
	"CopilotActions",
	"CopilotSearches",
	"VulnerabilityOverview",
	"PatchTuesday",
	"ScaOverview",
	"ScaPolicies",
	"Indices",
	"Snapshots",
	"Graylog-Management",
	"Graylog-Metrics",
	"Graylog-Pipelines",
	"ReportCreation",
	"VulnerabilityReports",
	"SCAReports",
	"Healthcheck",
	"Metrics",
	"Connectors",
	"FileAnalysis",
	"CloudSecurityAssessment",
	"WebVulnerabilityAssessment",
	"GitHubAudit",
	// The Threat Intel drawer and the OpenCTI page became one page with a tab per
	// source (#1153); /opencti redirects to its OpenCTI tab.
	"ThreatIntel",
	// formerly in the avatar menu
	"License",
	"Users",
	"SSOConfig",
	"Scheduler",
	"CustomerPortal",
	"Logs",
	"Audit",
	"ExternalServices-ThirdPartyIntegrations",
	"ExternalServices-NetworkConnectors",
	"ExternalServices-ShuffleAppAuth",
	// Stack Provisioning opened a modal from the sidebar; it is a page now.
	"StackProvisioning",
	...PANEL_KEYS
]

/** Entries analysts could not use or see before, and still don't get. */
const ADMIN_ONLY = ["InternalNotifications", "MessageTemplates", "SSOConfig", "Audit"]

interface Leaf {
	key: string
	linkedRoute: string | null
}

function leaves(items: MenuMixedOption[]): Leaf[] {
	return items.flatMap(item => {
		const children = (item as { children?: MenuMixedOption[] }).children
		if (children) return leaves(children)
		const label = (item as { label?: unknown }).label
		// routerLinkItem renders h(RouterLink, { to: { name } }); panel entries have a plain string label.
		const vnode = typeof label === "function" ? (label as () => { props?: { to?: { name?: string } } })() : null
		return [{ key: String(item.key), linkedRoute: vnode?.props?.to?.name ?? null }]
	})
}

function allKeys(items: MenuMixedOption[]): string[] {
	return items.flatMap(item => {
		const children = (item as { children?: MenuMixedOption[] }).children
		return [String(item.key), ...(children ? allKeys(children) : [])]
	})
}

function routeNames(records: RouteRecordRaw[]): Set<string> {
	const names = new Set<string>()
	const walk = (list: RouteRecordRaw[]) => {
		for (const record of list) {
			if (typeof record.name === "string") names.add(record.name)
			if (record.children) walk(record.children)
		}
	}
	walk(records)
	return names
}

function menuFor(role: "admin" | "analyst") {
	auth.isAdmin = role === "admin"
	return getItems()
}

describe("sidebar menu", () => {
	it("still reaches every page the old menu reached", () => {
		const keys = leaves(menuFor("admin")).map(leaf => leaf.key)
		const missing = PREVIOUS_DESTINATIONS.filter(destination => !keys.includes(destination))
		expect(missing).toEqual([])
	})

	it("links every entry to a real route, keyed by that route's name", () => {
		const known = routeNames(routes)
		for (const leaf of leaves(menuFor("admin"))) {
			if (PANEL_KEYS.includes(leaf.key)) {
				expect(leaf.linkedRoute, `${leaf.key} opens a panel, not a page`).toBeNull()
				continue
			}
			expect(known.has(leaf.key), `${leaf.key} is not a route`).toBe(true)
			expect(leaf.linkedRoute, `${leaf.key} links to ${leaf.linkedRoute}`).toBe(leaf.key)
		}
	})

	it("never gives a section a route's name, which would highlight the section instead of the page", () => {
		const known = routeNames(routes)
		const leafKeys = new Set(leaves(menuFor("admin")).map(leaf => leaf.key))
		const sectionKeys = allKeys(menuFor("admin")).filter(key => !leafKeys.has(key))
		expect(sectionKeys.filter(key => known.has(key))).toEqual([])
	})

	it("has no duplicate keys", () => {
		const keys = allKeys(menuFor("admin"))
		expect(keys.filter((key, i) => keys.indexOf(key) !== i)).toEqual([])
	})

	it("gives analysts everything except the admin-only entries", () => {
		const admin = leaves(menuFor("admin")).map(leaf => leaf.key)
		const analyst = leaves(menuFor("analyst")).map(leaf => leaf.key)
		expect(admin.filter(key => !analyst.includes(key)).sort()).toEqual([...ADMIN_ONLY].sort())
	})

	it("drops a Platform group left empty for analysts rather than showing it bare", () => {
		const platform = menuFor("analyst").find(item => item.key === "Platform") as { children: MenuMixedOption[] }
		for (const group of platform.children) {
			const children = (group as { children?: MenuMixedOption[] }).children
			expect(children?.length, `${String(group.key)} is empty`).toBeGreaterThan(0)
		}
	})

	it("orders the sections the way the work happens", () => {
		expect(menuFor("admin").map(item => item.key)).toEqual([
			"Overview",
			"AiAnalyst",
			"Incidents",
			"Investigate",
			"Respond",
			"Detections",
			"Exposure",
			"Endpoints",
			"Customers",
			"Reports",
			"Platform"
		])
	})
})
