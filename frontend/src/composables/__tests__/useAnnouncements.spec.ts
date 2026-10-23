/**
 * SOCFortress announcements ("What's new"): one request per session, only for SOC roles, and the
 * seen ids kept per user in localStorage, pruned to what the feed still carries.
 */

import type { Announcement } from "@/types/announcements"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AuthUserRole } from "@/types/auth"

const getAnnouncements = vi.fn()
const auth = vi.hoisted(() => ({ userName: "alice", role: 2 }))

vi.mock("@/api", () => ({
	default: { announcements: { getAnnouncements: (...args: unknown[]) => getAnnouncements(...args) } }
}))
vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({
		userName: auth.userName,
		isRoleGranted: (roles: AuthUserRole[]) => roles.includes(auth.role) || (auth.role === 5 && roles.includes(2))
	})
}))

function announcement(id: string, overrides: Partial<Announcement> = {}): Announcement {
	return {
		id,
		category: "product",
		title: id,
		summary: "",
		body_markdown: "",
		image_url: null,
		image_alt: "",
		cta: null,
		published_at: "2026-10-20T00:00:00+00:00",
		expires_at: null,
		popup: false,
		...overrides
	}
}

function answer(items: Announcement[], enabled = true) {
	return { data: { success: true, message: "", enabled, announcements: items } }
}

async function fresh() {
	vi.resetModules()
	const mod = await import("../useAnnouncements")
	return mod
}

describe("useAnnouncements", () => {
	beforeEach(() => {
		getAnnouncements.mockReset()
		localStorage.clear()
		sessionStorage.clear()
		auth.userName = "alice"
		auth.role = AuthUserRole.Analyst
	})

	it("asks once for every caller", async () => {
		getAnnouncements.mockResolvedValue(answer([announcement("a")]))
		const { useAnnouncements } = await fresh()
		await Promise.all([useAnnouncements().load(), useAnnouncements().load()])
		expect(getAnnouncements).toHaveBeenCalledTimes(1)
		expect(useAnnouncements().announcements.value.map(a => a.id)).toEqual(["a"])
	})

	it.each([AuthUserRole.Admin, AuthUserRole.Analyst, AuthUserRole.Responder])("asks for SOC role %s", async role => {
		auth.role = role
		getAnnouncements.mockResolvedValue(answer([]))
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(getAnnouncements).toHaveBeenCalledTimes(1)
	})

	it.each([AuthUserRole.Scheduler, AuthUserRole.CustomerUser])("never asks for role %s", async role => {
		auth.role = role
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(getAnnouncements).not.toHaveBeenCalled()
	})

	it("shows nothing when the deployment turned announcements off", async () => {
		getAnnouncements.mockResolvedValue(answer([announcement("a")], false))
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(useAnnouncements().enabled.value).toBe(false)
		expect(useAnnouncements().announcements.value).toEqual([])
	})

	it("is silent on a failure and asks again next time", async () => {
		getAnnouncements.mockRejectedValueOnce(new Error("down")).mockResolvedValue(answer([announcement("a")]))
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(useAnnouncements().announcements.value).toEqual([])
		await useAnnouncements().load()
		expect(useAnnouncements().announcements.value.map(a => a.id)).toEqual(["a"])
	})

	it("keeps what a user has seen per user, across sessions", async () => {
		getAnnouncements.mockResolvedValue(answer([announcement("a"), announcement("b")]))
		let { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(useAnnouncements().unseen.value.map(a => a.id)).toEqual(["a", "b"])
		useAnnouncements().markSeen(["a"])
		expect(useAnnouncements().unseen.value.map(a => a.id)).toEqual(["b"])

		;({ useAnnouncements } = await fresh())
		await useAnnouncements().load()
		expect(useAnnouncements().unseen.value.map(a => a.id)).toEqual(["b"])

		auth.userName = "bob"
		;({ useAnnouncements } = await fresh())
		await useAnnouncements().load()
		expect(useAnnouncements().unseen.value.map(a => a.id)).toEqual(["a", "b"])
	})

	it("forgets seen ids the feed no longer carries", async () => {
		localStorage.setItem("copilot.announcements.seen.alice", JSON.stringify(["gone", "a"]))
		getAnnouncements.mockResolvedValue(answer([announcement("a")]))
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(JSON.parse(localStorage.getItem("copilot.announcements.seen.alice") || "[]")).toEqual(["a"])
	})

	it("survives a corrupt stored value", async () => {
		localStorage.setItem("copilot.announcements.seen.alice", "{not json")
		getAnnouncements.mockResolvedValue(answer([announcement("a")]))
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		expect(useAnnouncements().unseen.value.map(a => a.id)).toEqual(["a"])
	})

	it("queues only unseen popup items for the modal", async () => {
		getAnnouncements.mockResolvedValue(
			answer([announcement("p1", { popup: true }), announcement("quiet"), announcement("p2", { popup: true })])
		)
		const { useAnnouncements } = await fresh()
		await useAnnouncements().load()
		useAnnouncements().markSeen(["p2"])
		expect(useAnnouncements().popupQueue.value.map(a => a.id)).toEqual(["p1"])
	})

	it("forgets everything at logout", async () => {
		getAnnouncements.mockResolvedValue(answer([announcement("a")]))
		const { useAnnouncements, resetAnnouncements } = await fresh()
		await useAnnouncements().load()
		useAnnouncements().rememberModalShown()
		resetAnnouncements()
		expect(useAnnouncements().announcements.value).toEqual([])
		expect(useAnnouncements().modalAlreadyShown()).toBe(false)
		await useAnnouncements().load()
		expect(getAnnouncements).toHaveBeenCalledTimes(2)
	})
})
