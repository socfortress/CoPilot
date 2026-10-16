/**
 * Talon v2 action proposals in the chat (plan M5-11b; talon-analyst SPEC §5.3 M5-11, §9.5).
 *
 * - Pure helpers: what a proposal's state means (final, blocking the thread), its labels, the
 *   provenance warnings, a comment split into text and highlighted links, the open calls of a
 *   thread.
 * - The module-level record of the proposals the cards have read (`rememberAction`), which the
 *   conversation derives its "waiting for a decision" and its resume from, and the resume guard
 *   (`claimResume`). Both are cleared at logout (`stores/auth.ts:setLogout`).
 *
 * Every string a proposal carries reaches the page as text, never as HTML or Markdown.
 */
import type { TalonAction, TalonActionProvenance } from "@/types/talonActions"
import type { TalonV2ChatMessage, TalonV2ToolState } from "@/types/talonV2"
import { reactive } from "vue"

/** How often an open card reads its record again, until nothing more can change. */
export const TALON_APPROVAL_POLL_MS = 10_000

// ── states ───────────────────────────────────────────────────────────────────

/** talon-analyst's final statuses: its record can't change any more, and the thread doesn't wait on it. */
export const TALON_FINAL = new Set(["executed", "failed", "denied", "expired", "withdrawn"])

/**
 * CoPilot states from which CoPilot moves the row no further, whatever talon-analyst's record says:
 * `refused` (the record changed, or talon-analyst refused the decision) and `unreported` (the
 * result couldn't be posted within its window).
 */
export const COPILOT_SETTLED = new Set(["refused", "unreported"])

/** Nothing more will change for this proposal: the card stops polling. */
export function isSettled(action: TalonAction): boolean {
	return TALON_FINAL.has(action.talon_status) || COPILOT_SETTLED.has(action.state)
}

/**
 * The thread waits on it: talon-analyst answers the thread's turns 409 while a record is `pending`,
 * or `approved` without its result (SPEC §9.5 "A turn while one waits").
 */
export function blocksThread(action: TalonAction): boolean {
	return !TALON_FINAL.has(action.talon_status)
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

// ── a comment's links ────────────────────────────────────────────────────────

/**
 * What a comment shows as a link: a scheme (`https://`, `hxxp://`, `ftp://`…), `www.`, or a host
 * name followed by a path, broadly as talon-analyst sets `links` (`talon.tools.actions._LINK`).
 * Highlighted only: it never becomes an `<a>` and nothing fetches it.
 */
const LINK = /(?:\b[a-z][a-z0-9+.-]*:\/\/|\bwww\.)[^\s<>"'`]+|\b[\w-]+(?:\.[\w-]+)+\/[^\s<>"'`]*/gi

const TRAILING = /[.,;:!?)\]}]+$/

export interface TextSegment {
	text: string
	link: boolean
}

/** `text` split into plain runs and link runs, in order; joined they are `text` exactly. */
export function linkSegments(text: string): TextSegment[] {
	const out: TextSegment[] = []
	let last = 0
	for (const match of text.matchAll(LINK)) {
		const start = match.index ?? 0
		// Punctuation that ends a sentence or closes a bracket isn't part of the link.
		const link = match[0].replace(TRAILING, "")
		if (!link) continue
		if (start > last) out.push({ text: text.slice(last, start), link: false })
		out.push({ text: link, link: true })
		last = start + link.length
	}
	if (last < text.length) out.push({ text: text.slice(last), link: false })
	return out
}

// ── times ────────────────────────────────────────────────────────────────────

/** CoPilot's naive UTC `DATETIME` (no offset) as a time; one with an offset as it says. Null if unreadable. */
export function parseUtc(value: string | null | undefined): Date | null {
	if (!value) return null
	const withZone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
	const date = new Date(withZone)
	return Number.isNaN(date.getTime()) ? null : date
}

/** "3h 59m", "4m 10s", "12s": the time left until `until`; null once it has passed. */
export function timeLeft(until: Date | null, now: number): string | null {
	if (!until) return null
	const seconds = Math.floor((until.getTime() - now) / 1000)
	if (seconds <= 0) return null
	const h = Math.floor(seconds / 3600)
	const m = Math.floor((seconds % 3600) / 60)
	const s = seconds % 60
	if (h) return `${h}h ${m}m`
	if (m) return `${m}m ${s}s`
	return `${s}s`
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

// ── what the cards have read (module-level, cleared at logout) ──────────────

export interface CardRecord {
	action: TalonAction | null
	/** The card's read failed for good (a 404): it tells the thread nothing. */
	failed: boolean
}

const cards = reactive(new Map<string, CardRecord>())
const resumed = new Set<string>()

/** A card read (or was answered) this proposal: the newest record wins. */
export function rememberAction(action: TalonAction) {
	cards.set(action.id, { action, failed: false })
}

/** A card couldn't read its proposal at all (404): it no longer holds the thread. */
export function forgetAction(approvalId: string) {
	cards.set(approvalId, { action: cards.get(approvalId)?.action ?? null, failed: true })
}

export function knownAction(approvalId: string): CardRecord | undefined {
	return cards.get(approvalId)
}

/**
 * The thread's resume for this set of proposals is to be sent now: true once per key for the whole
 * session, so re-renders, polls and remounts can't send it twice.
 */
export function claimResume(threadId: string, approvalIds: string[]): boolean {
	const key = `${threadId}:${[...approvalIds].sort().join(",")}`
	if (resumed.has(key)) return false
	resumed.add(key)
	return true
}

/** Forget every proposal and resume (logout, or a test). */
export function resetTalonActions() {
	cards.clear()
	resumed.clear()
}
