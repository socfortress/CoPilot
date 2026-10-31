import type { TalonChatThread, TalonCheckedItem } from "@/types/talonChat"
import { codeFrom } from "@/api/talonChatStream"
import { i18nGlobal } from "@/lang"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

/**
 * "Ask Talon" (talon-analyst D97): how the page words what Talon sends, in the user's language.
 *
 * Errors are localized by their machine `code` only (talon-analyst SPEC §8 "Errors carry a code"):
 * the English `detail` beside it is never shown or matched. The "checked" summary is built from
 * fixed kinds; a kind or type the portal doesn't know is left out, never shown raw.
 */

/** The codes the portal words itself; anything else reads as `unknown`. */
export const ERROR_CODES = [
	"invalid_request",
	"invalid_headers",
	"not_portal_role",
	"portal_role_refused",
	"customer_not_accessible",
	"portal_off",
	"settings_unavailable",
	"thread_not_found",
	"thread_archived",
	"access_removed",
	"thread_limit",
	"new_thread_limit",
	"alert_not_found",
	"body_too_large",
	"message_too_long",
	"busy_thread",
	"busy_user",
	"busy",
	"turn_limit",
	"timeout",
	"budget_customer",
	"budget_portal",
	"budget_portal_user",
	"messages_customer",
	"messages_user",
	"budget_unavailable",
	"failed",
	"draft_not_found",
	"draft_expired",
	"draft_conflict",
	"read_only",
	"soc_requests_off",
	"soc_request_limit",
	"soc_request_cooldown",
	"invalid_question",
	"not_found",
	"internal_failure",
	"stream_closed",
	"network",
	"unknown"
] as const

export type TalonChatErrorCode = (typeof ERROR_CODES)[number]

const KNOWN_CODES = new Set<string>(ERROR_CODES)

/** The code as the page words it: a known one, else `unknown`. */
export function knownCode(code: string | null | undefined): TalonChatErrorCode {
	return code && KNOWN_CODES.has(code) ? (code as TalonChatErrorCode) : "unknown"
}

/** The user's words for a refusal or a failed turn, by its code. */
export function errorText(code: string | null | undefined): string {
	return i18nGlobal.t(`talonChat.errors.${knownCode(code)}`)
}

/**
 * The code of a refused HTTP request (CoPilot's own or talon-analyst's, both `{detail, code}` at the
 * top level): `network` when no answer came, null when the answer carries none.
 */
export function errorCodeOf(err: unknown): string | null {
	const response = (err as { response?: { data?: unknown } } | null)?.response
	if (!response) return "network"
	const data = response.data
	return typeof data === "object" && data !== null ? codeFrom((data as { code?: unknown }).code) : null
}

const KINDS = new Set([
	"alert",
	"alert_list",
	"report",
	"assets",
	"event_search",
	"event",
	"earlier_result",
	"soc_draft",
	"analysis_offer"
])
const INTEL_TYPES = new Set(["ip", "domain", "url", "hash", "cve", "technique", "opencti_object"])

/** One item of the summary in words ("2 event searches"); null for a kind the portal doesn't know. */
export function checkedPhrase(item: TalonCheckedItem): string | null {
	const t = i18nGlobal.t
	const count = item.count
	if (item.kind === "intel") {
		const type = item.type && INTEL_TYPES.has(item.type) ? item.type : "other"
		return t(`talonChat.checked.intel.${type}`, { count }, count)
	}
	if (!KINDS.has(item.kind)) return null
	return t(`talonChat.checked.kinds.${item.kind}`, { count }, count)
}

/** "Checked: the alert, 2 event searches, 1 IP address"; null when there is nothing to say. */
export function checkedLine(items: TalonCheckedItem[] | null | undefined): string | null {
	const phrases = (items ?? []).map(checkedPhrase).filter((p): p is string => !!p)
	if (!phrases.length) return null
	return i18nGlobal.t("talonChat.checked.line", { items: phrases.join(", ") })
}

/** The most a portal message may hold (talon-analyst `TALON_PORTAL_CHAT_MAX_MESSAGE_CHARS`). */
export const MESSAGE_MAX = 4000

/** Characters as the server counts them (code points, not UTF-16 units). */
export function messageLength(text: string): number {
	return [...(text ?? "").trim()].length
}

/** A thread's title, or "Conversation of <its start>" when it has none yet. */
export function threadTitle(thread: Pick<TalonChatThread, "title" | "created_at">): string {
	if (thread.title) return thread.title
	const date = String(formatDate(thread.created_at, useSettingsStore().dateFormat.datetime, { tz: true }))
	return i18nGlobal.t("talonChat.threads.untitled", { date })
}
