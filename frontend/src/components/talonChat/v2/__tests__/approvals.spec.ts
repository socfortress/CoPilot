/**
 * The approval helpers (M5-11b): which states are final, hold a thread (an approved record only
 * inside its result window) or are read slowly; untrusted text with its invisible and
 * direction-changing characters escaped; a comment's links (never holding such a character, their
 * hosts in punycode); CoPilot's times and the expiry by its own clock; a thread's open calls.
 */
import type { TalonV2ChatMessage } from "@/types/talonV2"
import { describe, expect, it } from "vitest"
import {
	blocksThread,
	escapeOf,
	expiryDeadline,
	hasHiddenChars,
	isWithdrawable,
	linkSegments,
	openApprovals,
	parseUtc,
	pollClass,
	provenanceWarnings,
	punycodeLink,
	safeSegments,
	stateLabel,
	timeLeft
} from "../approvals"
import { naiveUtc, talonAction } from "./fixtures"

const RLO = "\u202E"

function shown(segments: ReturnType<typeof linkSegments>) {
	return segments.map(s => s.text).join("")
}

describe("talon approval helpers", () => {
	it.each([
		["pending", "pending", "active", true],
		["claiming", "pending", "active", true],
		["executing", "approved", "active", true],
		["executed", "approved", "active", true],
		["executed", "executed", "final", false],
		["failed", "failed", "final", false],
		["denied", "denied", "final", false],
		["expired", "expired", "final", false],
		["withdrawn", "withdrawn", "final", false],
		["refused", "pending", "slow", true],
		["unreported", "approved", "slow", true],
		["claim_lost", "approved", "active", true]
	])("state %s, talon %s: polled %s, holds the thread %s", (state, talon_status, poll, blocks) => {
		const action = talonAction({ state, talon_status, result_due_by: naiveUtc(23) })
		expect(pollClass(action)).toBe(poll)
		expect(blocksThread(action)).toBe(blocks)
	})

	it("an approved record holds the thread only until its result window ends", () => {
		const action = talonAction({ state: "unreported", talon_status: "approved", result_due_by: naiveUtc(1) })
		const due = parseUtc(action.result_due_by)?.getTime() as number
		expect(blocksThread(action, due - 1000)).toBe(true)
		expect(pollClass(action, due - 1000)).toBe("slow")
		expect(blocksThread(action, due)).toBe(false)
		expect(pollClass(action, due + 1000)).toBe("final")
		// No window known: it holds the thread (talon-analyst would say 409).
		expect(blocksThread(talonAction({ talon_status: "approved", result_due_by: null }))).toBe(true)
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

	it.each([
		["\u200B", "⟨U+200B⟩"],
		["\u200F", "⟨U+200F⟩"],
		["\u202A", "⟨U+202A⟩"],
		[RLO, "⟨U+202E⟩"],
		["\u2066", "⟨U+2066⟩"],
		["\u2069", "⟨U+2069⟩"],
		["\uFEFF", "⟨U+FEFF⟩"],
		["\u061C", "⟨U+061C⟩"],
		["\u180E", "⟨U+180E⟩"],
		["\u00AD", "⟨U+00AD⟩"],
		["\u{E0041}", "⟨U+E0041⟩"]
	])("hidden character %j is shown as %s", (char, escape) => {
		expect(hasHiddenChars(`a${char}b`)).toBe(true)
		expect(escapeOf(char)).toBe(escape)
		expect(safeSegments(`a${char}b`)).toEqual([
			{ kind: "text", text: "a" },
			{ kind: "escape", text: escape, char },
			{ kind: "text", text: "b" }
		])
	})

	it("plain text has nothing hidden", () => {
		expect(hasHiddenChars("ACME — an ordinary reason, ünïcödé and 日本語")).toBe(false)
		expect(safeSegments("plain")).toEqual([{ kind: "text", text: "plain" }])
		expect(safeSegments("")).toEqual([])
	})

	it("a comment's links: highlighted runs, the rest kept exactly", () => {
		const text = "Go to https://a.example/x. Then www.b.example; then c.example/d) and ftp://e.example, done"
		const segments = linkSegments(text)
		expect(shown(segments)).toBe(text)
		expect(segments.filter(s => s.kind === "link").map(s => s.text)).toEqual([
			"https://a.example/x",
			"www.b.example",
			"c.example/d",
			"ftp://e.example"
		])
		expect(linkSegments("no links here, just a.dot")).toEqual([{ kind: "text", text: "no links here, just a.dot" }])
	})

	it("a right-to-left override can't forge a link: the link ends at it and it is escaped", () => {
		const forged = `https://evil.invalid/${RLO}moc.tfosorcim.www//:sptth`
		const segments = linkSegments(forged)
		// The real link ends at the override; what follows reads as it is stored, backwards.
		expect(segments.filter(s => s.kind === "link").map(s => s.text)).toEqual([
			"https://evil.invalid/",
			"moc.tfosorcim.www//:sptth"
		])
		expect(segments.some(s => s.kind === "escape" && s.text === "⟨U+202E⟩")).toBe(true)
		expect(shown(segments)).not.toContain(RLO)
		expect(shown(segments)).toBe("https://evil.invalid/⟨U+202E⟩moc.tfosorcim.www//:sptth")
	})

	it("a zero-width character splits a link and is escaped", () => {
		const segments = linkSegments("https://micro\u200Bsoft.com/login")
		expect(segments.filter(s => s.kind === "link").map(s => s.text)).toEqual(["https://micro", "soft.com/login"])
		expect(shown(segments)).toBe("https://micro⟨U+200B⟩soft.com/login")
	})

	it("an IDN host is shown in punycode, the rest as written", () => {
		// Cyrillic "о"s in a look-alike of microsoft.com.
		const lookalike = "https://micrоsоft.com/login?x=1"
		const [link] = linkSegments(lookalike).filter(s => s.kind === "link")
		expect(link.text).toMatch(/^https:\/\/xn--micrsft-[a-z0-9]+\.com\/login\?x=1$/)
		expect(link.kind === "link" && link.punycode).toBe(true)
		expect(punycodeLink("www.bücher.example/path").text).toBe("www.xn--bcher-kva.example/path")
		expect(punycodeLink("https://user@bücher.example:8443/").text).toBe("https://user@xn--bcher-kva.example:8443/")
		expect(punycodeLink("https://plain.example/ü")).toEqual({ text: "https://plain.example/ü", punycode: false })
	})

	it("naive times from CoPilot are UTC; one with an offset as it says", () => {
		expect(parseUtc("2026-10-16T12:00:00")?.toISOString()).toBe("2026-10-16T12:00:00.000Z")
		expect(parseUtc("2026-10-16T12:00:00+02:00")?.toISOString()).toBe("2026-10-16T10:00:00.000Z")
		expect(parseUtc("2026-10-16T12:00:00Z")?.toISOString()).toBe("2026-10-16T12:00:00.000Z")
		expect(parseUtc("not a time")).toBeNull()
		expect(parseUtc(null)).toBeNull()
	})

	it("the expiry counts from CoPilot's seconds left, not from the browser's clock", () => {
		const received = 1_000_000
		// expires_at says one thing (a skewed browser would read it wrongly); the seconds left win.
		const action = talonAction({ expires_at: "2000-01-01T00:00:00", expires_in_seconds: 90 })
		expect(expiryDeadline(action, received)).toBe(received + 90_000)
		const fallback = talonAction({ expires_in_seconds: undefined, expires_at: "2026-10-16T12:00:00" })
		expect(expiryDeadline(fallback, received)).toBe(Date.parse("2026-10-16T12:00:00Z"))
		expect(
			expiryDeadline(talonAction({ expires_in_seconds: undefined, expires_at: "garbage" }), received)
		).toBeNull()
	})

	it("time left", () => {
		const until = 1_000_000_000
		expect(timeLeft(until, until - (3 * 3600 + 59 * 60) * 1000)).toBe("3h 59m")
		expect(timeLeft(until, until - 250_000)).toBe("4m 10s")
		expect(timeLeft(until, until - 12_000)).toBe("12s")
		expect(timeLeft(until, until)).toBeNull()
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
})
