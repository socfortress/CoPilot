/**
 * The approval helpers (M5-11b): which states are final, hold a thread (an approved record only
 * inside its result window) or are read slowly; untrusted text with its invisible and
 * direction-changing characters escaped; a comment's links (never holding such a character, their
 * hosts in punycode); CoPilot's times and the expiry by its own clock; a thread's open calls.
 * Endpoint actions (EA-4): labels, host targets, risk labels, the shape, a command's counts, first
 * line and runs (tabs, trailing spaces, unseen characters), a collection's parameters.
 */
import type { TalonActionProvenance } from "@/types/talonActions"
import type { TalonV2ChatMessage } from "@/types/talonV2"
import { describe, expect, it } from "vitest"
import {
	actionLabel,
	blocksThread,
	collectionParameters,
	commandCounts,
	commandSegments,
	commandShape,
	countsText,
	endpointKind,
	escapeOf,
	expiryDeadline,
	firstContentLine,
	hasHiddenChars,
	hasUnseenChars,
	isHostAction,
	isWithdrawable,
	linkSegments,
	lookalikes,
	lookalikeWarnings,
	openApprovals,
	parseUtc,
	pollClass,
	provenanceWarnings,
	punycodeLink,
	riskLabelled,
	riskLabels,
	safeSegments,
	shellOf,
	shellOs,
	stateLabel,
	timeLeft,
	whitespaceCounts,
	wrapSegments
} from "../approvals"
import { collectAction, commandAction, naiveUtc, talonAction } from "./fixtures"

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
		expect(
			provenanceWarnings({ endpoint_output_used: true, copied_from_output: true }).map(w => [w.flag, w.severity])
		).toEqual([
			["copied_from_output", "error"],
			["endpoint_output_used", "warning"]
		])
		expect(
			provenanceWarnings({
				endpoint_output_used: "true",
				copied_from_output: 1
			} as unknown as TalonActionProvenance)
		).toEqual([])
	})

	it("collections and commands are host actions, with their own labels", () => {
		for (const action of ["quarantine_host", "release_host", "collect_artifact", "endpoint_command"]) {
			expect(isHostAction({ action }), action).toBe(true)
		}
		for (const action of ["set_alert_status", "assign_alert", "comment_on_alert", "something_else"]) {
			expect(isHostAction({ action }), action).toBe(false)
		}
		expect(actionLabel("collect_artifact")).toBe("Collect a Velociraptor artifact")
		expect(actionLabel("endpoint_command")).toBe("Run a command on the endpoint")
		expect(endpointKind(collectAction())).toEqual({
			kind: "collection",
			label: "Collection",
			detail: "Windows.System.Pslist"
		})
		expect(endpointKind(commandAction("x"))).toEqual({ kind: "command", label: "Command", detail: "PowerShell" })
		expect(endpointKind(talonAction())).toBeNull()
	})

	it("the shells by CoPilot's command artifacts; anything else is none", () => {
		expect(shellOf("Windows.System.PowerShell")).toBe("PowerShell")
		expect(shellOf("Linux.Sys.BashShell")).toBe("bash")
		expect(shellOf("Windows.System.CmdShell")).toBe("cmd")
		expect(shellOf("Windows.System.Pslist")).toBeNull()
		expect(shellOf(undefined)).toBeNull()
	})

	it("risk labels: known ones in words, unknown ones as written, each once, strings only", () => {
		expect(riskLabels({ risk_labels: ["network_fetch", "made_up", "network_fetch", 3, null] })).toEqual([
			{ key: "network_fetch", text: "Network fetch", known: true },
			{ key: "made_up", text: "made_up", known: false }
		])
		expect(
			riskLabels({
				risk_labels: [
					"delete_or_kill",
					"registry_or_service",
					"account_change",
					"persistence",
					"shutdown_or_reboot"
				]
			}).map(r => r.text)
		).toEqual([
			"Deletes or kills",
			"Registry or service change",
			"Account change",
			"Persistence",
			"Shutdown or reboot"
		])
		expect(riskLabels({ risk_labels: "network_fetch" })).toEqual([])
		expect(riskLabels({ risk_labels: ["toString", "constructor"] }).every(r => !r.known)).toBe(true)
		expect(riskLabels(null)).toEqual([])
	})

	it("the shape is read-only only when the record says exactly that", () => {
		expect(commandShape({ shape: "read-only" })).toBe("read-only")
		expect(commandShape({ shape: "free-form" })).toBe("free-form")
		for (const shape of [undefined, null, "", "READ-ONLY", "read only", true]) {
			expect(commandShape({ shape }), String(shape)).toBe("unknown")
		}
		expect(commandShape(undefined)).toBe("unknown")
	})

	it("a command's counts as talon-analyst measures them, and its first line", () => {
		expect(commandCounts("Get-Process")).toEqual({ lines: 1, chars: 11 })
		expect(commandCounts("a\nb\nc\n\n")).toEqual({ lines: 3, chars: 7 })
		expect(commandCounts("\u{1F600}")).toEqual({ lines: 1, chars: 1 })
		expect(countsText("a")).toBe("1 line, 1 character")
		expect(countsText(`${"x".repeat(1999)}\n`)).toBe("1 line, 2,000 characters")
		expect(firstContentLine("one\ntwo")).toEqual({ line: 1, text: "one" })
		expect(firstContentLine("only")).toEqual({ line: 1, text: "only" })
		// Blank lines (spaces, tabs, any Zs) are skipped; the first with content is named by its number.
		expect(firstContentLine("\n \t\u00A0\n  two\nthree")).toEqual({ line: 3, text: "  two" })
		// An invisible character is content: it is shown escaped, not skipped.
		expect(firstContentLine("\n\u200B\nx")).toEqual({ line: 2, text: "\u200B" })
		expect(firstContentLine("\n  \n")).toEqual({ line: 1, text: "" })
	})

	it("a command's runs mark tabs, trailing whitespace, space runs, non-ASCII and unseen characters", () => {
		const command = "a\tb  \n  \t \nc\rd\u202Ee\n"
		expect(commandSegments(command)).toEqual([
			[
				{ kind: "text", text: "a" },
				{ kind: "tab", text: "\t" },
				{ kind: "text", text: "b" },
				{ kind: "trailing", text: "  " }
			],
			[
				{ kind: "trailing", text: "  " },
				{ kind: "tab", text: "\t", trailing: true },
				{ kind: "trailing", text: " " }
			],
			[
				{ kind: "text", text: "c" },
				{ kind: "escape", text: "⟨U+000D⟩", char: "\r" },
				{ kind: "text", text: "d" },
				{ kind: "escape", text: "⟨U+202E⟩", char: "\u202E" },
				{ kind: "text", text: "e" }
			],
			[]
		])
		expect(commandSegments("a    b c  d     ")).toEqual([
			[
				{ kind: "text", text: "a" },
				{ kind: "spaces", text: "⟨␠×4⟩", count: 4, trailing: false },
				{ kind: "text", text: "b c  d" },
				{ kind: "spaces", text: "⟨␠×5⟩", count: 5, trailing: true }
			]
		])
		expect(commandSegments("Proc\u0435ss\u00A0")).toEqual([
			[
				{ kind: "text", text: "Proc" },
				{ kind: "nonascii", text: "\u0435" },
				{ kind: "text", text: "ss" },
				{ kind: "escape", text: "⟨U+00A0⟩", char: "\u00A0", trailing: true }
			]
		])
		const plain = "Get-Process | Select-Object -First 5 \n\tWhere-Object {$_.CPU -gt 1}"
		expect(
			commandSegments(plain)
				.map(line => line.map(s => s.text).join(""))
				.join("\n")
		).toBe(plain)
		expect(whitespaceCounts(command)).toEqual({ tabs: 2, trailingLines: 2, spaceRuns: 0 })
		expect(whitespaceCounts("a     b\u2003")).toEqual({ tabs: 0, trailingLines: 1, spaceRuns: 1 })
	})

	it.each([
		["\r"],
		["\u0000"],
		["\u001B"],
		["\u007F"],
		["\u202E"],
		["\u200B"],
		["\u2028"],
		["\u2029"],
		["\uD800"],
		["\u00A0"],
		["\u2003"],
		["\u3000"],
		["\u202F"],
		["\u3164"],
		["\uFFA0"],
		["\u115F"],
		["\uFE0F"],
		["\u{E0100}"],
		["\u2800"],
		["\u00AD"]
	])("%j is a character nobody can see, escaped in a command", char => {
		expect(hasUnseenChars(`a${char}b`)).toBe(true)
		expect(commandSegments(`a${char}b`)[0][1]).toEqual({ kind: "escape", text: escapeOf(char), char })
	})

	it("tab, newline, space and visible non-ASCII are not unseen", () => {
		expect(hasUnseenChars("a\tb\nc d")).toBe(false)
		expect(hasUnseenChars("\u0435\u00E9\u4E2D")).toBe(false)
	})

	it("a line is cut into rows of at most the given columns; escapes and marks are never cut", () => {
		const rows = wrapSegments([{ kind: "text", text: "abcdefghij" }], 4)
		expect(rows.map(row => row.map(s => s.text).join(""))).toEqual(["abcd", "efgh", "ij"])
		const mixed = wrapSegments(
			[
				{ kind: "text", text: "abc" },
				{ kind: "escape", text: "⟨U+00A0⟩", char: "\u00A0" },
				{ kind: "tab", text: "\t" },
				{ kind: "spaces", text: "⟨␠×9⟩", count: 9, trailing: true }
			],
			8
		)
		// "⟨␠×9⟩" takes 5 columns: after the tab's 4 it doesn't fit in 8.
		expect(mixed.map(row => row.map(s => s.kind))).toEqual([["text"], ["escape"], ["tab"], ["spaces"]])
		expect(wrapSegments([], 8)).toEqual([[]])
		// Code points, not UTF-16 units: an emoji is never split.
		expect(
			wrapSegments([{ kind: "nonascii", text: "\u{1F600}\u{1F600}\u{1F600}" }], 4).map(r => r[0].text)
		).toEqual(["\u{1F600}\u{1F600}", "\u{1F600}"])
	})

	it("look-alikes: non-ASCII counted, scripts listed, right-to-left found", () => {
		expect(lookalikes("Get-Process")).toEqual({ nonAscii: 0, scripts: ["Latin"], rtl: false })
		expect(lookalikes("Get-Proc\u0435ss")).toEqual({ nonAscii: 1, scripts: ["Latin", "Cyrillic"], rtl: false })
		expect(lookalikes("\u03BFpen")).toEqual({ nonAscii: 1, scripts: ["Latin", "Greek"], rtl: false })
		expect(lookalikes("echo \u05E9")).toEqual({ nonAscii: 1, scripts: ["Latin", "Hebrew"], rtl: true })
		expect(lookalikes("\u0627").rtl).toBe(true)
		// By code point, so a script newer than the browser's Unicode tables counts too.
		expect(lookalikes("x\u{10D00}").rtl).toBe(true)
		expect(lookalikes("\u{1E900}").rtl).toBe(true)
		expect(lookalikes("\uFB1D").rtl).toBe(true)
		expect(lookalikes("\uFE70").rtl).toBe(true)
		expect(lookalikes("\u08FF").rtl).toBe(true)
		expect(lookalikes("\u058F\u0900\uFB1C\u{107FF}\u{11000}").rtl).toBe(false)
		expect(lookalikes("caf\u00E9")).toEqual({ nonAscii: 1, scripts: ["Latin"], rtl: false })
		expect(lookalikeWarnings("caf\u00E9").map(w => w.flag)).toEqual(["non_ascii"])
		expect(lookalikeWarnings("Get-Process")).toEqual([])
		expect(lookalikeWarnings("a\u0435", "A parameter value")[0].text).toBe(
			"A parameter value holds 1 non-ASCII character, highlighted: a look-alike letter can make it read as something it isn't."
		)
	})

	it("the shell's OS, and whether risk labels were given at all", () => {
		expect(shellOs("Windows.System.PowerShell")).toBe("windows")
		expect(shellOs("Windows.System.CmdShell")).toBe("windows")
		expect(shellOs("Linux.Sys.BashShell")).toBe("linux")
		expect(shellOs("Windows.System.Pslist")).toBeNull()
		expect(riskLabelled({ risk_labels: [] })).toBe(true)
		expect(riskLabelled({ risk_labels: "network_fetch" })).toBe(false)
		expect(riskLabelled({})).toBe(false)
		expect(riskLabelled(null)).toBe(false)
	})

	it("a collection's parameters as rows; any other shape is not ok", () => {
		expect(
			collectionParameters({
				env: [
					{ key: "ProcessRegex", value: "x" },
					{ key: "Limit", value: 5 }
				]
			})
		).toEqual({
			ok: true,
			rows: [
				{ key: "ProcessRegex", value: "x" },
				{ key: "Limit", value: "5" }
			]
		})
		expect(collectionParameters(undefined)).toEqual({ ok: true, rows: [] })
		expect(collectionParameters({ env: [] })).toEqual({ ok: true, rows: [] })
		for (const odd of [
			{ ProcessRegex: "x" },
			{ env: [{ key: "a", value: "b" }], extra: 1 },
			{ env: [{ key: 1, value: "b" }] },
			{ env: [{ key: "a", value: "b", note: "c" }] },
			{ env: "a" },
			["a"],
			"a"
		]) {
			expect(collectionParameters(odd).ok, JSON.stringify(odd)).toBe(false)
		}
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
