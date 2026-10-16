/**
 * What the v2 chat says when CoPilot or talon-analyst refuses a thread's request before anything
 * ran (talon-analyst SPEC §8 "v2 API": the chat's pre-stream refusals and the read-back's).
 *
 * Every text shown is fixed here: talon-analyst's own `detail` is only matched, never displayed,
 * for the refusals the UI acts on. Anything else shows its short `detail` as text (CoPilot's proxy
 * already reduced it to talon-analyst's one-line reason or "Talon request failed").
 */

/** talon-analyst's fixed reasons (`talon.chat`, `talon.actions`), as CoPilot passes them through. */
export const REASON_REVOKED = "access to this thread's customer was removed"
export const REASON_TAGS_NARROWED = "your alert access changed since this thread began; start a new thread"
export const REASON_ARCHIVED = "this thread is archived"
export const REASON_NOT_FOUND = "thread not found"

export const NOTICE_REVOKED = "Access to this thread's customer was removed. You can still rename or archive it."
export const NOTICE_TAGS_NARROWED = "Your alert access changed since this thread began; start a new thread."
export const NOTICE_REFUSED = "Talon refused this thread. Start a new thread."
export const NOTICE_PENDING =
	"Waiting for a decision: an action in this thread needs a decision in CoPilot before Talon can go on."
export const NOTICE_ARCHIVED = "This thread is archived. You can read it, but not continue it."
export const NOTICE_GONE = "This thread no longer exists."

export type NoticeKind = "blocked" | "pending" | "archived" | "gone" | "error"

export interface ThreadNotice {
	kind: NoticeKind
	text: string
	/** The thread can't take another message: the composer is disabled. */
	locksComposer: boolean
}

/** The notice for a refusal with this status and `detail`. */
export function noticeFor(status: number | null, detail: string): ThreadNotice {
	if (status === 403) {
		if (detail === REASON_REVOKED) return { kind: "blocked", text: NOTICE_REVOKED, locksComposer: true }
		if (detail === REASON_TAGS_NARROWED) return { kind: "blocked", text: NOTICE_TAGS_NARROWED, locksComposer: true }
		return { kind: "blocked", text: NOTICE_REFUSED, locksComposer: true }
	}
	if (status === 409) {
		if (detail === REASON_ARCHIVED) return { kind: "archived", text: NOTICE_ARCHIVED, locksComposer: true }
		return { kind: "pending", text: NOTICE_PENDING, locksComposer: false }
	}
	if (status === 404) return { kind: "gone", text: NOTICE_GONE, locksComposer: true }
	return { kind: "error", text: detail, locksComposer: false }
}
