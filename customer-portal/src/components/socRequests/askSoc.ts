import type { SocRequest, SocRequestAlertTarget, SocRequestStatus, SocRequestUrgency } from "@/types/socRequests"
import { i18nGlobal } from "@/lang"

/**
 * "Ask the SOC" (#1305): what the form checks before sending, and how a question reads.
 * The checks are the backend's (`schema/soc_requests.py:clean_question`), so a question the
 * form accepts is never refused for its text.
 */

export const QUESTION_MAX = 2000

// Controls other than tab and newline, and the formatting characters (bidi overrides,
// zero-width) that would make the SOC read something other than what the user sees. Code
// points, not a regular expression: a character class would put them in the source as is.
const FORMAT_CODE_POINTS = new Set(
	["200B", "200C", "200D", "200E", "200F", "202A", "202B", "202C", "202D", "202E", "2066", "2067", "2068", "2069"]
		.concat(["FEFF", "061C"])
		.map(hex => Number.parseInt(hex, 16))
)
const TAB = 9
const NEWLINE = 10
const DELETE = 127

function forbidden(char: string): boolean {
	const code = char.codePointAt(0) ?? 0
	if (code === TAB || code === NEWLINE) return false
	return code < 32 || code === DELETE || FORMAT_CODE_POINTS.has(code)
}

/** The question as it will be sent: Windows line ends folded, trimmed. */
export function normalizeQuestion(text: string): string {
	return (text ?? "").replace(/\r\n/g, "\n").trim()
}

/** Characters as the backend counts them (code points, not UTF-16 units). */
export function questionLength(text: string): number {
	return [...normalizeQuestion(text)].length
}

/** Why the question can't be sent, or null when it can. */
export function questionProblem(text: string): string | null {
	const question = normalizeQuestion(text)
	const t = i18nGlobal.t
	if (!question) return t("socRequests.problem.empty")
	if ([...question].length > QUESTION_MAX) return t("socRequests.problem.tooLong", { max: QUESTION_MAX })
	if ([...question].some(forbidden)) return t("socRequests.problem.characters")
	return null
}

// Labels are getters, read in the user's language when shown (#1310).
export const URGENCY_OPTIONS: { value: SocRequestUrgency; label: string; description: string }[] = (
	["low", "normal", "high"] as const
).map(value => ({
	value,
	get label() {
		return i18nGlobal.t(`socRequests.urgency.${value}`)
	},
	get description() {
		return i18nGlobal.t(`socRequests.urgency.${value}Hint`)
	}
}))

export const URGENCY_LABELS: Record<SocRequestUrgency, string> = {
	get low() {
		return i18nGlobal.t("socRequests.urgency.low")
	},
	get normal() {
		return i18nGlobal.t("socRequests.urgency.normal")
	},
	get high() {
		return i18nGlobal.t("socRequests.urgency.high")
	}
}

export const STATUS_LABELS: Record<SocRequestStatus, string> = {
	get open() {
		return i18nGlobal.t("socRequests.status.open")
	},
	get answered() {
		return i18nGlobal.t("socRequests.status.answered")
	}
}

/** Where a question on an alert can go: the alert's open case (or a new one), or the alert itself. */
export function targetOptions(openCaseId: number | null | undefined): {
	value: SocRequestAlertTarget
	label: string
	description: string
}[] {
	const t = i18nGlobal.t
	return [
		openCaseId
			? {
					value: "case",
					label: t("socRequests.target.addToCase", { id: openCaseId }),
					description: t("socRequests.target.addToCaseHint")
				}
			: {
					value: "case",
					label: t("socRequests.target.openCase"),
					description: t("socRequests.target.openCaseHint")
				},
		{ value: "alert", label: t("socRequests.target.alertOnly"), description: t("socRequests.target.alertOnlyHint") }
	]
}

/** Where a listed question was filed, when that isn't the page it is shown on. */
export function filedOn(request: SocRequest, entity: "alert" | "case"): string | null {
	if (entity === "alert") return request.case_id ? i18nGlobal.t("socRequests.filed.onCase", { id: request.case_id }) : null
	return request.origin_alert_id ? i18nGlobal.t("socRequests.filed.fromAlert", { id: request.origin_alert_id }) : null
}
