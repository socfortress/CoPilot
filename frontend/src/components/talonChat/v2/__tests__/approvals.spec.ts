/**
 * The approval helpers (M5-11b): which states are final or hold a thread, a comment's links (each
 * run of text kept exactly), CoPilot's naive UTC times, a thread's open calls, and the resume guard.
 */
import type { TalonV2ChatMessage } from "@/types/talonV2"
import { describe, expect, it } from "vitest"
import {
	blocksThread,
	claimResume,
	forgetAction,
	isSettled,
	isWithdrawable,
	knownAction,
	linkSegments,
	openApprovals,
	parseUtc,
	provenanceWarnings,
	rememberAction,
	resetTalonActions,
	stateLabel,
	timeLeft
} from "../approvals"
import { talonAction } from "./fixtures"

describe("talon approval helpers", () => {
	it.each([
		["pending", "pending", false, true],
		["claiming", "pending", false, true],
		["executing", "approved", false, true],
		["executed", "approved", false, true],
		["executed", "executed", true, false],
		["failed", "failed", true, false],
		["denied", "denied", true, false],
		["expired", "expired", true, false],
		["withdrawn", "withdrawn", true, false],
		["refused", "pending", true, true],
		["unreported", "approved", true, true],
		["claim_lost", "approved", false, true]
	])("state %s, talon %s: settled %s, holds the thread %s", (state, talon_status, settled, blocks) => {
		const action = talonAction({ state, talon_status })
		expect(isSettled(action)).toBe(settled)
		expect(blocksThread(action)).toBe(blocks)
	})

	it("withdraw only for the requester of a pending, unexpired proposal", () => {
		expect(isWithdrawable(talonAction())).toBe(true)
		expect(isWithdrawable(talonAction({ is_requester: false }))).toBe(false)
		expect(isWithdrawable(talonAction({ expired: true }))).toBe(false)
		expect(isWithdrawable(talonAction({ state: "claiming" }))).toBe(false)
		expect(isWithdrawable(talonAction({ talon_status: "approved" }))).toBe(false)
	})

	it("a pending proposal past its expiry reads expired", () => {
		expect(stateLabel(talonAction({ expired: true }))).toBe("Expired")
		expect(stateLabel(talonAction({ state: "something new" }))).toBe("something new")
	})

	it("provenance flags only when true", () => {
		expect(provenanceWarnings({ injection_detected: "yes" as unknown as boolean })).toEqual([])
		expect(provenanceWarnings(null)).toEqual([])
		expect(provenanceWarnings({ web_used: true }).map(w => w.flag)).toEqual(["web_used"])
	})

	it("a comment's links: highlighted runs, the text kept exactly", () => {
		const text = "Go to https://a.example/x. Then www.b.example; then c.example/d) and ftp://e.example, done"
		const segments = linkSegments(text)
		expect(segments.map(s => s.text).join("")).toBe(text)
		expect(segments.filter(s => s.link).map(s => s.text)).toEqual([
			"https://a.example/x",
			"www.b.example",
			"c.example/d",
			"ftp://e.example"
		])
		expect(linkSegments("no links here, just a.dot")).toEqual([{ text: "no links here, just a.dot", link: false }])
		expect(linkSegments("")).toEqual([])
	})

	it("coPilot's naive times are UTC; one with an offset as it says", () => {
		expect(parseUtc("2026-10-16T12:00:00")?.toISOString()).toBe("2026-10-16T12:00:00.000Z")
		expect(parseUtc("2026-10-16T12:00:00+02:00")?.toISOString()).toBe("2026-10-16T10:00:00.000Z")
		expect(parseUtc("2026-10-16T12:00:00Z")?.toISOString()).toBe("2026-10-16T12:00:00.000Z")
		expect(parseUtc("not a time")).toBeNull()
		expect(parseUtc(null)).toBeNull()
	})

	it("time left", () => {
		const until = new Date(1_000_000_000)
		expect(timeLeft(until, until.getTime() - (3 * 3600 + 59 * 60) * 1000)).toBe("3h 59m")
		expect(timeLeft(until, until.getTime() - 250_000)).toBe("4m 10s")
		expect(timeLeft(until, until.getTime() - 12_000)).toBe("12s")
		expect(timeLeft(until, until.getTime())).toBeNull()
		expect(timeLeft(null, 0)).toBeNull()
	})

	it("a thread's open calls: a card until a later turn answers its call", () => {
		const card = (id: string, call: string): TalonV2ChatMessage => ({
			id,
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [
				{
					kind: "tool",
					toolCallId: call,
					name: "x",
					state: "approval-requested",
					approval: { id: `ap-${call}`, status: "pending" }
				}
			]
		})
		const answer = (id: string, call: string): TalonV2ChatMessage => ({
			id,
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [{ kind: "tool", toolCallId: call, name: null, state: "output-denied" }]
		})
		expect(openApprovals([card("a", "c1")]).map(o => o.approvalId)).toEqual(["ap-c1"])
		expect(openApprovals([card("a", "c1"), answer("b", "c1")])).toEqual([])
		expect(openApprovals([card("a", "c1"), answer("b", "c1"), card("c", "c2")]).map(o => o.approvalId)).toEqual([
			"ap-c2"
		])
		expect(openApprovals([card("a", "c1")])[0].hint).toBe("pending")
	})

	it("the resume is claimed once per thread and set of proposals, until logout", () => {
		resetTalonActions()
		expect(claimResume("t1", ["b", "a"])).toBe(true)
		expect(claimResume("t1", ["a", "b"])).toBe(false)
		expect(claimResume("t1", ["a", "b", "c"])).toBe(true)
		expect(claimResume("t2", ["a", "b"])).toBe(true)
		rememberAction(talonAction())
		forgetAction("other")
		expect(knownAction(talonAction().id)?.action?.id).toBe(talonAction().id)
		expect(knownAction("other")?.failed).toBe(true)

		resetTalonActions() // stores/auth.ts:setLogout
		expect(knownAction(talonAction().id)).toBeUndefined()
		expect(claimResume("t1", ["a", "b"])).toBe(true)
	})
})
