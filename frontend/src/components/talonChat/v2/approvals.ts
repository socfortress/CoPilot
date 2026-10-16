/**
 * Talon v2 action proposals in the chat (plan M5-11b; talon-analyst SPEC §5.3 M5-11, §9.5): pure
 * helpers. What a proposal's state means (final, holding the thread, how often to read it), its
 * labels, the provenance warnings, untrusted text made safe to look at (invisible and
 * direction-changing characters shown as escapes; a comment's links highlighted, their hosts in
 * punycode), CoPilot's times, and a thread's open calls.
 *
 * The shared records, the page's poll and the resume guard are in `actionCards.ts`. Every string a
 * proposal carries reaches the page as text, never as HTML or Markdown.
 */
import type { TalonAction, TalonActionProvenance } from "@/types/talonActions"
import type { TalonV2ChatMessage, TalonV2ToolState } from "@/types/talonV2"

// ── states ───────────────────────────────────────────────────────────────────

/** talon-analyst's final statuses: its record can't change any more. */
export const TALON_FINAL = new Set(["executed", "failed", "denied", "expired", "withdrawn"])

/**
 * CoPilot states from which CoPilot moves the row no further, whatever talon-analyst's record says:
 * `refused` (the record changed, or talon-analyst refused the decision for everyone) and
 * `unreported` (the result couldn't be posted within its window).
 */
export const COPILOT_SETTLED = new Set(["refused", "unreported"])

/** CoPilot's naive UTC `DATETIME` (no offset) as a time; one with an offset as it says. Null if unreadable. */
export function parseUtc(value: string | null | undefined): Date | null {
	if (!value) return null
	const withZone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
	const date = new Date(withZone)
	return Number.isNaN(date.getTime()) ? null : date
}

/**
 * The thread waits on it: talon-analyst answers the thread's turns 409 while a record is `pending`,
 * or `approved` and still inside its result window (`result_due_by`; SPEC §9.5 "A turn while one
 * waits"). Past the window an approved record no longer holds the thread.
 */
export function blocksThread(action: TalonAction, now: number = Date.now()): boolean {
	if (TALON_FINAL.has(action.talon_status)) return false
	if (action.talon_status === "approved") {
		const due = parseUtc(action.result_due_by)
		if (due && now >= due.getTime()) return false
	}
	return true
}

/**
 * How the page's poll treats a proposal: `final`, nothing more can change; `slow`, CoPilot moves it
 * no further but talon-analyst's record isn't final (read now and then, so the thread heals);
 * `active`, it may change any moment.
 */
export function pollClass(action: TalonAction, now: number = Date.now()): "final" | "slow" | "active" {
	if (!blocksThread(action, now)) return "final"
	return COPILOT_SETTLED.has(action.state) ? "slow" : "active"
}

/** May still be withdrawn by its requester. */
export function isWithdrawable(action: TalonAction): boolean {
	return action.is_requester && action.state === "pending" && action.talon_status === "pending" && !action.expired
}

export function isHostAction(action: Pick<TalonAction, "action">): boolean {
	return action.action === "quarantine_host" || action.action === "release_host"
}

const ACTION_LABELS: Record<string, string> = {
	set_alert_status: "Set the alert's status",
	assign_alert: "Assign the alert",
	comment_on_alert: "Comment on the alert",
	quarantine_host: "Quarantine the host",
	release_host: "Release the host from quarantine"
}

export function actionLabel(action: string): string {
	return ACTION_LABELS[action] ?? action
}

const STATE_LABELS: Record<string, string> = {
	pending: "Waiting for a decision",
	claiming: "Being decided",
	claimed: "Approved, about to run",
	executing: "Running",
	executed: "Executed",
	failed: "Failed",
	denied: "Denied",
	expired: "Expired",
	withdrawn: "Withdrawn",
	refused: "Can no longer be decided",
	claim_lost: "Not run: the approval's answer was lost",
	unreported: "Run, but the outcome wasn't reported to Talon"
}

/** CoPilot's state of the proposal, in words. */
export function stateLabel(action: Pick<TalonAction, "state" | "expired">): string {
	if (action.state === "pending" && action.expired) return STATE_LABELS.expired
	return STATE_LABELS[action.state] ?? action.state
}

export type StateTone = "waiting" | "running" | "success" | "error" | "neutral"

export function stateTone(action: Pick<TalonAction, "state" | "expired">): StateTone {
	if (action.state === "pending") return action.expired ? "neutral" : "waiting"
	if (["claiming", "claimed", "executing"].includes(action.state)) return "running"
	if (action.state === "executed") return "success"
	if (["failed", "claim_lost", "refused", "unreported"].includes(action.state)) return "error"
	return "neutral"
}

// ── provenance ───────────────────────────────────────────────────────────────

export interface ProvenanceWarning {
	flag: "injection_detected" | "untrusted_seen" | "web_used"
	severity: "error" | "warning"
	text: string
}

export const PROVENANCE_INJECTION =
	"Talon's injection defender flagged text read in the turn that proposed this. Check the proposal against the alert or host yourself before approving."
export const PROVENANCE_UNTRUSTED =
	"Earlier in this thread Talon read text the injection defender flagged. The proposal may have been steered by it."
export const PROVENANCE_WEB = "This thread used text from the web. The proposal may have been shaped by it."

export function provenanceWarnings(provenance: TalonActionProvenance | null | undefined): ProvenanceWarning[] {
	const p = provenance ?? {}
	const out: ProvenanceWarning[] = []
	if (p.injection_detected === true) {
		out.push({ flag: "injection_detected", severity: "error", text: PROVENANCE_INJECTION })
	}
	if (p.untrusted_seen === true) out.push({ flag: "untrusted_seen", severity: "warning", text: PROVENANCE_UNTRUSTED })
	if (p.web_used === true) out.push({ flag: "web_used", severity: "warning", text: PROVENANCE_WEB })
	return out
}

// ── untrusted text ───────────────────────────────────────────────────────────

/**
 * Characters that are invisible or change the direction text is drawn in: every format character
 * (Cf: zero-width spaces and joiners, bidi embeddings, overrides and isolates, the BOM, the Arabic
 * letter mark, the Mongolian vowel separator, soft hyphens, tags…). Untrusted text shows them as `⟨U+202E⟩`, so a
 * right-to-left override can't make `evil.invalid/\u202Emoc.tfosorcim` read as `microsoft.com`.
 */
const HIDDEN = /\p{Cf}/u
const HIDDEN_ALL = /\p{Cf}/gu

export const HIDDEN_CHARS_WARNING =
	"This proposal holds invisible or direction-changing characters, shown as ⟨U+…⟩: its text may not read the way it looks."

export function hasHiddenChars(text: string | null | undefined): boolean {
	return !!text && HIDDEN.test(text)
}

/** `⟨U+202E⟩` for one hidden character. */
export function escapeOf(char: string): string {
	return `⟨U+${(char.codePointAt(0) ?? 0).toString(16).toUpperCase().padStart(4, "0")}⟩`
}

export type TextSegment =
	| { kind: "text"; text: string }
	/** A hidden character, shown as its escape; `char` is the character itself. */
	| { kind: "escape"; text: string; char: string }
	/** A link, highlighted and never clickable; `text` is how it is shown (its host in punycode). */
	| { kind: "link"; text: string; raw: string; punycode: boolean }

/** `text` as plain runs and escapes for its hidden characters. */
export function safeSegments(text: string): TextSegment[] {
	const out: TextSegment[] = []
	let last = 0
	for (const match of text.matchAll(HIDDEN_ALL)) {
		const start = match.index ?? 0
		if (start > last) out.push({ kind: "text", text: text.slice(last, start) })
		out.push({ kind: "escape", text: escapeOf(match[0]), char: match[0] })
		last = start + match[0].length
	}
	if (last < text.length) out.push({ kind: "text", text: text.slice(last) })
	return out
}

/**
 * What a comment shows as a link: a scheme (`https://`, `hxxp://`, `ftp://`…), `www.`, or a host
 * name followed by a path, broadly as talon-analyst sets `links` (`talon.tools.actions._LINK`).
 * A link never holds a hidden character: it ends at one, and the character is shown escaped.
 */
const NOT_IN_LINK = String.raw`[^\s<>"'\x60\p{Cf}]`
const LINK = new RegExp(
	String.raw`(?:\b[a-z][a-z0-9+.-]*:\/\/|\bwww\.)${NOT_IN_LINK}+|\b[\p{L}\p{N}_-]+(?:\.[\p{L}\p{N}_-]+)+\/${NOT_IN_LINK}*`,
	"giu"
)
const TRAILING = /[.,;:!?)\]}]+$/
// eslint-disable-next-line no-control-regex
const NON_ASCII = /[^\x00-\x7F]/

/** A link with its host in punycode (`xn--…`), as a browser would resolve it; as it is if it can't be. */
export function punycodeLink(link: string): { text: string; punycode: boolean } {
	const schemeEnd = link.indexOf("://")
	const start = schemeEnd > 0 && /^[a-z][a-z0-9+.-]*$/i.test(link.slice(0, schemeEnd)) ? schemeEnd + 3 : 0
	const after = link.slice(start)
	const stop = after.search(/[/?#]/)
	const authority = stop < 0 ? after : after.slice(0, stop)
	const rest = stop < 0 ? "" : after.slice(stop)
	const at = authority.lastIndexOf("@")
	const userinfo = authority.slice(0, at + 1)
	const hostport = authority.slice(at + 1)
	if (!NON_ASCII.test(hostport)) return { text: link, punycode: false }
	try {
		const host = new URL(`http://${hostport}`).host
		return { text: `${link.slice(0, start)}${userinfo}${host}${rest}`, punycode: host !== hostport }
	} catch {
		return { text: link, punycode: false }
	}
}

/** A comment: plain runs, escapes for hidden characters, and its links (hosts in punycode). */
export function linkSegments(text: string): TextSegment[] {
	const out: TextSegment[] = []
	let last = 0
	for (const match of text.matchAll(LINK)) {
		const start = match.index ?? 0
		// Punctuation that ends a sentence or closes a bracket isn't part of the link.
		const raw = match[0].replace(TRAILING, "")
		if (!raw) continue
		if (start > last) out.push(...safeSegments(text.slice(last, start)))
		const shown = punycodeLink(raw)
		out.push({ kind: "link", text: shown.text, raw, punycode: shown.punycode })
		last = start + raw.length
	}
	if (last < text.length) out.push(...safeSegments(text.slice(last)))
	return out
}

// ── times ────────────────────────────────────────────────────────────────────

/** "3h 59m", "4m 10s", "12s": the time left until `until` (ms); null once it has passed. */
export function timeLeft(until: number | null, now: number): string | null {
	if (until === null) return null
	const seconds = Math.floor((until - now) / 1000)
	if (seconds <= 0) return null
	const h = Math.floor(seconds / 3600)
	const m = Math.floor((seconds % 3600) / 60)
	const s = seconds % 60
	if (h) return `${h}h ${m}m`
	if (m) return `${m}m ${s}s`
	return `${s}s`
}

/**
 * When a pending proposal expires, by this browser's clock: CoPilot's `expires_in_seconds` counted
 * from when its answer arrived (so a skewed clock doesn't move it), else `expires_at`; null if
 * neither can be read.
 */
export function expiryDeadline(action: TalonAction, receivedAt: number): number | null {
	if (typeof action.expires_in_seconds === "number" && Number.isFinite(action.expires_in_seconds)) {
		return receivedAt + action.expires_in_seconds * 1000
	}
	return parseUtc(action.expires_at)?.getTime() ?? null
}

// ── a thread's open calls ────────────────────────────────────────────────────

const ANSWERED = new Set<TalonV2ToolState>(["output-available", "output-error", "output-denied"])

export interface OpenApproval {
	approvalId: string
	toolCallId: string
	/** The stream's or the read-back's status of the card: a hint until the card has read the record. */
	hint: string
}

/**
 * The approval cards of a thread whose calls no later turn has answered yet, in order. A resumed
 * call's answer comes in the turn that resumed it, by the same call id and without a card (SPEC §8
 * "Reading turns back"), so a card followed by its answer is closed.
 */
export function openApprovals(messages: TalonV2ChatMessage[]): OpenApproval[] {
	const open = new Map<string, OpenApproval>()
	for (const message of messages) {
		if (message.role !== "assistant") continue
		for (const item of message.items) {
			if (item.kind !== "tool") continue
			if (item.approval) {
				open.set(item.toolCallId, {
					approvalId: item.approval.id,
					toolCallId: item.toolCallId,
					hint: item.approval.status
				})
			} else if (ANSWERED.has(item.state)) {
				open.delete(item.toolCallId)
			}
		}
	}
	return [...open.values()]
}
