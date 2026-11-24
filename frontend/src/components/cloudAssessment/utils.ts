/**
 * Cloud security assessment (#1328): labels, ordering and wording shared by the page and the
 * customer's Cloud Accounts section. Pure: no Vue, no API.
 */
import type {
	CloudAccount,
	CloudAuthMethod,
	CloudCheckStatus,
	CloudComplianceFramework,
	CloudProvider,
	CloudRequirementStatus,
	CloudScan,
	CloudScanCounts,
	CloudScanStatus,
	CloudSeverity
} from "@/types/cloud-assessment"

export const PROVIDERS: CloudProvider[] = ["aws", "azure", "gcp", "m365"]

export const PROVIDER_LABELS: Record<CloudProvider, string> = {
	aws: "AWS",
	azure: "Azure",
	gcp: "Google Cloud",
	m365: "Microsoft 365"
}

/** Only `carbon:`, `mdi:` and `logos:` icons are bundled. */
export const PROVIDER_ICONS: Record<CloudProvider, string> = {
	aws: "logos:aws",
	azure: "logos:microsoft-azure",
	gcp: "logos:google-cloud",
	m365: "logos:microsoft-icon"
}

/** What the account identifier is, per provider: the first line of an account's facts. */
export const CLOUD_ACCOUNT_LABELS: Record<CloudProvider, string> = {
	aws: "AWS account",
	azure: "Tenant",
	gcp: "Project",
	m365: "Tenant"
}

export const AUTH_METHODS: Record<CloudProvider, CloudAuthMethod[]> = {
	aws: ["role", "access_keys"],
	azure: ["client_secret"],
	gcp: ["service_account_key"],
	m365: ["client_secret"]
}

export const AUTH_LABELS: Record<CloudAuthMethod, string> = {
	role: "IAM role with an External ID",
	access_keys: "Access keys",
	client_secret: "App registration and client secret",
	service_account_key: "Service account key"
}

/** The same, short enough for a narrow cell (the full label goes in its title). */
export const AUTH_SHORT_LABELS: Record<CloudAuthMethod, string> = {
	role: "IAM role",
	access_keys: "Access keys",
	client_secret: "Client secret",
	service_account_key: "Service account key"
}

export const SEVERITIES: CloudSeverity[] = ["critical", "high", "medium", "low", "informational", "unknown"]

export const SEVERITY_LABELS: Record<CloudSeverity, string> = {
	critical: "Critical",
	high: "High",
	medium: "Medium",
	low: "Low",
	informational: "Informational",
	unknown: "Unknown"
}

/** Naive UI tag types: an icon or a word always goes with the colour, never the colour alone. */
export type TagType = "default" | "error" | "warning" | "info" | "success"

export const SEVERITY_TAGS: Record<CloudSeverity, TagType> = {
	critical: "error",
	high: "error",
	medium: "warning",
	low: "info",
	informational: "default",
	unknown: "default"
}

/**
 * The fill of each severity's bar. The theme's status colours, as SOC Management's severity dots use
 * them: every bar sits beside its severity's name and count, so the colour is never all that says it.
 */
export const SEVERITY_FILLS: Record<CloudSeverity, string> = {
	critical: "bg-error",
	high: "bg-error",
	medium: "bg-warning",
	low: "bg-info",
	informational: "bg-border",
	unknown: "bg-border"
}

export const ACTIVE_STATUSES: CloudScanStatus[] = ["queued", "starting", "running", "ingesting"]

export const SCAN_STATUS_LABELS: Record<CloudScanStatus, string> = {
	queued: "Queued",
	starting: "Starting",
	running: "Running",
	ingesting: "Storing results",
	completed: "Completed",
	failed: "Failed",
	cancelled: "Cancelled"
}

export const SCAN_STATUS_TAGS: Record<CloudScanStatus, TagType> = {
	queued: "default",
	starting: "info",
	running: "info",
	ingesting: "info",
	completed: "success",
	failed: "error",
	cancelled: "default"
}

export const SCAN_STATUS_ICONS: Record<CloudScanStatus, string> = {
	queued: "carbon:time",
	starting: "carbon:in-progress",
	running: "carbon:in-progress",
	ingesting: "carbon:data-base",
	completed: "carbon:checkmark-outline",
	failed: "carbon:warning-alt",
	cancelled: "carbon:close-outline"
}

export const CHECK_STATUS_LABELS: Record<CloudCheckStatus, string> = {
	fail: "Failing",
	manual: "Manual review",
	pass: "Passing",
	muted: "Muted",
	no_findings: "Nothing to check"
}

export const CHECK_STATUS_TAGS: Record<CloudCheckStatus, TagType> = {
	fail: "error",
	manual: "warning",
	pass: "success",
	muted: "default",
	no_findings: "default"
}

export const REQUIREMENT_STATUS_LABELS: Record<CloudRequirementStatus, string> = {
	fail: "Failing",
	manual: "Manual review",
	pass: "Passing",
	not_assessed: "Not assessed"
}

export const REQUIREMENT_STATUS_TAGS: Record<CloudRequirementStatus, TagType> = {
	fail: "error",
	manual: "warning",
	pass: "success",
	not_assessed: "default"
}

export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

/** A credential within this many days of its expiry is flagged. */
export const EXPIRY_WARNING_DAYS = 30

export function isActive(status: CloudScanStatus | null | undefined): boolean {
	return !!status && ACTIVE_STATUSES.includes(status)
}

/** Whether a scan of the account can be started now (the backend checks again). */
export function canScan(account: CloudAccount): boolean {
	return account.enabled && !isActive(account.last_scan?.status) && (account.secret_configured || account.auth_method === "role")
}

export function failedBySeverity(counts: CloudScanCounts): Record<CloudSeverity, number> {
	return {
		critical: counts.failed_critical,
		high: counts.failed_high,
		medium: counts.failed_medium,
		low: counts.failed_low,
		informational: counts.failed_informational,
		unknown: counts.failed_unknown
	}
}

export interface SeveritySegment {
	severity: CloudSeverity
	count: number
	/** Share of the failures, 0–100. */
	percent: number
}

/** The failures' shares by severity, worst first, leaving out severities with none. */
export function severitySegments(counts: CloudScanCounts): SeveritySegment[] {
	const by = failedBySeverity(counts)
	const total = SEVERITIES.reduce((sum, severity) => sum + by[severity], 0)
	if (!total) return []
	return SEVERITIES.filter(severity => by[severity] > 0).map(severity => ({
		severity,
		count: by[severity],
		percent: (by[severity] / total) * 100
	}))
}

/** Passed checks' share of those with an outcome (passed + failed), 0–100, or null with none. */
export function passRate(counts: CloudScanCounts): number | null {
	const decided = counts.passed + counts.failed
	return decided ? Math.round((counts.passed / decided) * 100) : null
}

export function scheduleText(account: Pick<CloudAccount, "schedule" | "schedule_hour" | "schedule_weekday">): string {
	if (account.schedule === "off" || account.schedule_hour === null) return "Not scheduled"
	const hour = `${String(account.schedule_hour).padStart(2, "0")}:00 UTC`
	if (account.schedule === "weekly") return `Weekly, ${WEEKDAYS[account.schedule_weekday ?? 0]} at ${hour}`
	return `Daily at ${hour}`
}

export type ExpiryState = "expired" | "soon" | "ok" | "unknown"

export function expiryState(account: Pick<CloudAccount, "secret_expires_in_days" | "secret_expires_at">): ExpiryState {
	if (!account.secret_expires_at || account.secret_expires_in_days === null) return "unknown"
	if (account.secret_expires_in_days < 0) return "expired"
	if (account.secret_expires_in_days <= EXPIRY_WARNING_DAYS) return "soon"
	return "ok"
}

export function durationText(seconds: number | null): string | null {
	if (seconds === null || seconds < 0) return null
	if (seconds < 60) return `${seconds} s`
	const minutes = Math.floor(seconds / 60)
	if (minutes < 60) return `${minutes} min ${seconds % 60} s`
	return `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}

/** A scan's one-line outcome, for lists: what failed and, but for a first scan, what changed. */
export function scanOutcome(scan: Pick<CloudScan, "status" | "counts" | "error_message" | "previous_scan_id">): string {
	if (scan.status === "completed") {
		const { failed, total, new_failed: added, resolved_failed: resolved } = scan.counts
		const outcome = failed ? `${failed} failed of ${total}` : `All ${total} passed`
		return scan.previous_scan_id === null ? `${outcome} · first scan` : `${outcome} · ${added} new, ${resolved} resolved`
	}
	if (scan.status === "failed") return scan.error_message ?? "Failed"
	return SCAN_STATUS_LABELS[scan.status]
}

/** "1.2" before "1.10": ids and versions compared as people read them. */
export function naturalCompare(a: string, b: string): number {
	return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
}

/** Frameworks by name, each family's newest version first (CIS 5.0 before CIS 1.4). */
export function frameworkOrder(a: CloudComplianceFramework, b: CloudComplianceFramework): number {
	const family = naturalCompare(a.framework ?? a.key, b.framework ?? b.key)
	if (family) return family
	return naturalCompare(b.version ?? "", a.version ?? "") || naturalCompare(a.key, b.key)
}

/** An http(s) link from a scan's data, or null: nothing else becomes an `<a href>`. */
export function safeLink(value: string | null | undefined): string | null {
	if (!value) return null
	try {
		const url = new URL(value)
		return url.protocol === "https:" || url.protocol === "http:" ? url.href : null
	} catch {
		return null
	}
}

/** Prowler's CloudFormation template for the read-only ProwlerScan role, at a Prowler version. */
export function prowlerRoleTemplateUrl(prowlerVersion: string | null): string {
	const ref = prowlerVersion && /^\d+\.\d+\.\d+$/.test(prowlerVersion) ? prowlerVersion : "master"
	return `https://github.com/prowler-cloud/prowler/blob/${ref}/permissions/templates/cloudformation/prowler-scan-role.yml`
}
