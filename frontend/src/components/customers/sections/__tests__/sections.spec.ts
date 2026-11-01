import { describe, expect, it } from "vitest"
import {
	DEFAULT_SECTION,
	GROUPS,
	groupViews,
	searchSections,
	SECTION_IDS,
	sectionById,
	sectionPath,
	SECTIONS,
	sectionState,
	switchSummary,
	tabToSection,
	visibleSections
} from "../sections"
import { statusFixture } from "./fixtures"

const ALL = { admin: true, automation: true, wazuhWorker: true }

describe("the sections", () => {
	it("defines every id once, each in a known group", () => {
		expect(SECTIONS.map(section => section.id).sort()).toEqual([...SECTION_IDS].sort())
		const groups = new Set(GROUPS.map(group => group.id))
		for (const section of SECTIONS) expect(groups.has(section.group)).toBe(true)
		expect(sectionById(DEFAULT_SECTION).group).toBe("overview")
	})

	it("keeps the old tab names as ids, so ?tab= links still open them", () => {
		expect(tabToSection("IOC Enrichment")).toBe("IOC Enrichment")
		expect(tabToSection("Portal Branding")).toBe("Portal Branding")
		expect(tabToSection("Agents")).toBe("Agents")
		expect(tabToSection("Wazuh Worker")).toBe("Wazuh Worker")
		// The old parent tab of every customer setting opens its first one.
		expect(tabToSection("Customer")).toBe("Info")
		expect(tabToSection("nope")).toBeNull()
		expect(tabToSection(undefined)).toBeNull()
		expect(tabToSection("")).toBeNull()
	})

	it("shows Security to admins, AI Automation with Talon v2, Wazuh Worker with a stack", () => {
		const none = visibleSections({ admin: false, automation: false, wazuhWorker: false }).map(section => section.id)
		expect(none).not.toContain("Security")
		expect(none).not.toContain("AI Automation")
		expect(none).not.toContain("Wazuh Worker")
		const all = visibleSections(ALL).map(section => section.id)
		expect(all).toEqual(expect.arrayContaining(["Security", "AI Automation", "Wazuh Worker"]))
	})
})

describe("groupViews", () => {
	it("keeps the group order and splits a group into its subgroups", () => {
		const views = groupViews(visibleSections(ALL))
		expect(views.map(group => group.id)).toEqual(["overview", "agents", "data", "automation", "reports", "portal"])
		const portal = views.find(group => group.id === "portal")
		expect(portal?.subgroups.map(subgroup => subgroup.label)).toEqual([
			"Appearance",
			"Portal pages",
			"AI & requests",
			"Notifications"
		])
		expect(portal?.sections).toHaveLength(10)
		const data = views.find(group => group.id === "data")
		expect(data?.subgroups).toEqual([{ label: "", sections: data?.sections }])
	})

	it("leaves out a group with nothing to show", () => {
		const views = groupViews(SECTIONS.filter(section => section.group !== "reports"))
		expect(views.map(group => group.id)).not.toContain("reports")
	})
})

describe("sectionState", () => {
	const status = statusFixture()

	it("words a switch, the languages and the AI report with its chat", () => {
		expect(sectionState(sectionById("SLA"), status)).toEqual({ kind: "switch", on: true, word: "On" })
		expect(sectionState(sectionById("Activity"), status)).toEqual({ kind: "switch", on: false, word: "Off" })
		expect(sectionState(sectionById("Portal Languages"), status)).toEqual({
			kind: "switch",
			on: false,
			word: "English only"
		})
		expect(
			sectionState(sectionById("Portal Languages"), statusFixture({ portal_languages: { on: true, count: 3 } }))
		).toEqual({ kind: "switch", on: true, word: "3 languages" })
		expect(sectionState(sectionById("AI Report"), status)?.word).toBe("On · chat on")
		expect(
			sectionState(sectionById("AI Report"), statusFixture({ portal_ai_report: { on: true, chat_on: false } }))?.word
		).toBe("On")
	})

	it("counts a list with its noun", () => {
		expect(sectionState(sectionById("Event Sources"), status)).toEqual({ kind: "count", count: 1, word: "1 source" })
		expect(sectionState(sectionById("WAF"), status)?.word).toBe("3 WAFs")
		expect(sectionState(sectionById("Network Connectors"), status)?.word).toBe("None")
	})

	it("has nothing to say without a status, or for a section with none", () => {
		expect(sectionState(sectionById("SLA"), null)).toBeNull()
		expect(sectionState(sectionById("Info"), status)).toBeNull()
	})
})

describe("switchSummary", () => {
	it("counts the switches that are on, when there are at least two", () => {
		const portal = SECTIONS.filter(section => section.group === "portal")
		expect(switchSummary(portal, statusFixture())).toBe("7 of 10 on")
		expect(switchSummary([sectionById("AI Triggers")], statusFixture())).toBeNull()
		expect(switchSummary(portal, null)).toBeNull()
	})
})

describe("searchSections", () => {
	const all = visibleSections(ALL)

	it("finds by name first, then by keyword or group", () => {
		expect(searchSections("audit", all).map(section => section.id)).toEqual(["Audit Log"])
		expect(searchSections("virustotal", all).map(section => section.id)).toEqual(["IOC Enrichment"])
		const notifications = searchSections("notif", all).map(section => section.id)
		expect(notifications.slice(0, 3)).toEqual(["Notification Workflows", "Notifications", "Portal Notifications"])
		expect(searchSections("portal notifications", all).map(section => section.id)).toEqual(["Portal Notifications"])
	})

	it("ignores case and accents, and an empty query finds nothing", () => {
		expect(searchSections("SÉCURITY", all).map(section => section.id)).toEqual(["Security"])
		expect(searchSections("   ", all)).toEqual([])
	})

	it("finds only what the viewer may open", () => {
		const analyst = visibleSections({ admin: false, automation: false, wazuhWorker: false })
		expect(searchSections("security", analyst)).toEqual([])
	})
})

describe("sectionPath", () => {
	it("names the group and the subgroup", () => {
		expect(sectionPath(sectionById("IOC Enrichment"))).toEqual(["Customer Portal", "AI & requests"])
		expect(sectionPath(sectionById("WAF"))).toEqual(["Data sources"])
	})
})
