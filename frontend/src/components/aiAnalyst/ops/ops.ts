// The Talon Ops tab's pure helpers: labels, which action a finding's status allows, the mute window,
// the evidence as rows, and what a failure shows. Every time from the API is ISO 8601 (UTC).
//
// `why` and `recommendation` are a model's text (talon-analyst SPEC §5.7: "CoPilot must show them as
// text, never render them as Markdown or HTML"): the components bind them as text only, never with
// `v-html` or `Markdown`; nothing here turns them into markup either.
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type { TalonOpsEvidenceValue, TalonOpsFinding, TalonOpsSeverity, TalonOpsStatus } from "@/types/talonOps"

export const OPS_DOCS = "https://docs.socfortress.co/power-features/talon-ops"
/** The backend's text for a Talon without the ops API (`services/talon_ops.py:OLD_TALON`). */
export const OLD_TALON_OPS_TEXT =
	"This Talon has no ops API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
export const V2_OFF_TEXT =
	"Talon v2 is off in CoPilot, so Talon's ops findings can't be shown. An admin can turn it on."
export const OPS_OFF_TITLE = "Ops jobs are off in Talon"
export const OPS_OFF_TEXT =
	"No ops job is enabled in talon-analyst. Set TALON_OPS_JOBS=quiet_endpoints,silent_log_sources on every Talon api and worker container, then restart Talon."
export const PAGE_SIZE = 50
/** talon-analyst refuses a mute further away than this (`api/ops.py:MUTE_MAX`). */
export const MUTE_MAX_DAYS = 90
const DAY_MS = 24 * 60 * 60 * 1000

export const SEVERITIES: { value: TalonOpsSeverity; label: string; tag: "error" | "warning" | "info" | "default" }[] = [
	{ value: "high", label: "High", tag: "error" },
	{ value: "medium", label: "Medium", tag: "warning" },
	{ value: "low", label: "Low", tag: "info" },
	{ value: "info", label: "Info", tag: "default" }
]

export const STATUSES: { value: TalonOpsStatus; label: string; icon: string }[] = [
	{ value: "open", label: "Open", icon: "carbon:circle-dash" },
	{ value: "acknowledged", label: "Acknowledged", icon: "carbon:checkmark-outline" },
	{ value: "muted", label: "Muted", icon: "carbon:notification-off" },
	{ value: "resolved", label: "Resolved", icon: "carbon:checkmark-filled" }
]

/** The phase-1 jobs' names, until the jobs list says otherwise. */
export const JOB_LABELS: Record<string, string> = {
	quiet_endpoints: "Endpoints gone quiet",
	silent_log_sources: "Log sources gone silent"
}

export const KIND_LABELS: Record<string, string> = {
	never_connected: "Never connected",
	wazuh_quiet: "Wazuh quiet",
	velociraptor_quiet: "Velociraptor quiet",
	wazuh_only: "Wazuh only",
	velociraptor_only: "Velociraptor only",
	silent: "Silent",
	dropped: "Volume dropped",
	no_data: "No data"
}

export function severityInfo(severity: string | null | undefined) {
	return (
		SEVERITIES.find(s => s.value === severity) ?? { value: severity, label: severity || "Unknown", tag: "default" }
	)
}

export function statusInfo(status: string | null | undefined) {
	return STATUSES.find(s => s.value === status) ?? { value: status, label: status || "Unknown", icon: "carbon:help" }
}

export function jobLabel(
	job: string | null | undefined,
	titles: Record<string, string | null | undefined> = {}
): string {
	if (!job) return "Unknown job"
	return titles[job] || JOB_LABELS[job] || job
}

export function kindLabel(kind: string | null | undefined): string {
	if (!kind) return "Unknown"
	return KIND_LABELS[kind] ?? kind.replace(/_/g, " ")
}

/** Where a finding belongs: its customer, or the platform (admins only). */
export function customerText(customerCode: string | null | undefined): string {
	return customerCode ?? "Platform"
}

// ── actions ───────────────────────────────────────────────────────────────────

/**
 * talon-analyst's transitions (`api/ops.py`): acknowledge from open or muted; mute from open,
 * acknowledged or muted; reopen from acknowledged or muted. A resolved finding takes none.
 */
export function canAcknowledge(status: TalonOpsStatus | null | undefined): boolean {
	return status === "open" || status === "muted"
}

export function canMute(status: TalonOpsStatus | null | undefined): boolean {
	return status === "open" || status === "acknowledged" || status === "muted"
}

export function canReopen(status: TalonOpsStatus | null | undefined): boolean {
	return status === "acknowledged" || status === "muted"
}

/** Whether `until` (ms) is a mute end talon-analyst accepts: in the future, at most 90 days away. */
export function isValidMuteUntil(until: number | null | undefined, now = Date.now()): boolean {
	return typeof until === "number" && Number.isFinite(until) && until > now && until <= now + MUTE_MAX_DAYS * DAY_MS
}

/** The mute picker's default: a week from now. */
export function defaultMuteUntil(now = Date.now()): number {
	return now + 7 * DAY_MS
}

// ── the evidence ──────────────────────────────────────────────────────────────

export interface EvidenceRow {
	key: string
	/** A scalar or a list of scalars, as text. */
	text: string | null
	/** A nested object or a list of objects, as indented JSON (still text). */
	json: string | null
}

function isScalar(value: TalonOpsEvidenceValue): boolean {
	return value === null || ["string", "number", "boolean"].includes(typeof value)
}

function scalarText(value: TalonOpsEvidenceValue): string {
	if (value === null) return "—"
	if (typeof value === "boolean") return value ? "yes" : "no"
	return String(value)
}

/** The evidence as rows for a key-value list, in the job's order. */
export function evidenceRows(evidence: Record<string, TalonOpsEvidenceValue> | null | undefined): EvidenceRow[] {
	if (!evidence) return []
	return Object.entries(evidence).map(([key, value]) => {
		if (isScalar(value)) return { key, text: scalarText(value), json: null }
		if (Array.isArray(value) && value.every(isScalar)) {
			return { key, text: value.length ? value.map(scalarText).join(", ") : "none", json: null }
		}
		return { key, text: null, json: JSON.stringify(value, null, 2) }
	})
}

export function evidenceJson(finding: Pick<TalonOpsFinding, "evidence"> | null | undefined): string {
	return JSON.stringify(finding?.evidence ?? null, null, 2)
}

// ── what a failure shows ──────────────────────────────────────────────────────

export interface OpsProblem {
	kind: "v2_off" | "unsupported" | "error"
	title: string
	text: string
}

export function problemState(failure: TalonOpsFailure | null | undefined): OpsProblem | null {
	if (!failure) return null
	if (failure.code === "v2_off") return { kind: "v2_off", title: "Talon v2 is off", text: V2_OFF_TEXT }
	if (failure.code === "unsupported") {
		return { kind: "unsupported", title: "This Talon has no ops jobs", text: OLD_TALON_OPS_TEXT }
	}
	return { kind: "error", title: "Couldn't load Talon's ops data", text: failure.detail }
}
