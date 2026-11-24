/**
 * The cloud account form's model, checks and payloads (#1328). Pure: no Vue, no API.
 *
 * The credential is write-only: an edit starts with every credential field empty, and an empty
 * field keeps the stored credential (nothing is sent). The backend checks everything again with
 * the runner's own patterns; these checks only catch what can be told before saving.
 */
import type {
	CloudAccount,
	CloudAccountConfigInput,
	CloudAccountCreatePayload,
	CloudAccountSecret,
	CloudAccountUpdatePayload,
	CloudAuthMethod,
	CloudProvider,
	CloudSchedule
} from "@/types/cloud-assessment"
import { AUTH_METHODS } from "../utils"

export interface AccountForm {
	name: string
	provider: CloudProvider
	auth_method: CloudAuthMethod
	role_arn: string
	regions: string[]
	tenant_id: string
	client_id: string
	subscription_ids: string[]
	tenant_domain: string
	project_ids: string[]
	excluded_project_ids: string[]
	organization_id: string
	excluded_checks: string[]
	excluded_services: string[]
	timeout_minutes: number | null
	access_key_id: string
	secret_access_key: string
	client_secret: string
	/** A GCP service-account key file's JSON, pasted or read from the file. */
	gcp_key_text: string
	/** An AWS role assumed with CoPilot's host identity: no keys. */
	use_host_identity: boolean
	/** A client secret's expiry, as a timestamp (the date picker's value). */
	secret_expires_at: number | null
	enabled: boolean
	schedule: CloudSchedule
	schedule_hour: number
	schedule_weekday: number
}

export const ROLE_ARN = /^arn:aws(-cn|-us-gov|-iso|-iso-b|-iso-e|-iso-f|-eusc)?:iam::\d{12}:role\/([\w+=,.@-]+\/)*[\w+=,.@-]{1,64}$/
export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export const AWS_REGION = /^[a-z]{2,4}(-[a-z]+)+-\d{1,2}$/
export const AWS_KEY_ID = /^AKIA[A-Z0-9]{16}$/
export const DOMAIN = /^([A-Z0-9]([A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}$/i
export const GCP_PROJECT = /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/
export const CHECK_ID = /^[a-z0-9][a-z0-9_]{0,127}$/
export const SERVICE = /^[a-z0-9][a-z0-9_]{0,63}$/

/** AWS's commercial regions, offered in the picker; any other region name can be typed. */
export const AWS_REGIONS = [
	"us-east-1",
	"us-east-2",
	"us-west-1",
	"us-west-2",
	"ca-central-1",
	"ca-west-1",
	"mx-central-1",
	"sa-east-1",
	"eu-west-1",
	"eu-west-2",
	"eu-west-3",
	"eu-central-1",
	"eu-central-2",
	"eu-north-1",
	"eu-south-1",
	"eu-south-2",
	"il-central-1",
	"me-south-1",
	"me-central-1",
	"af-south-1",
	"ap-east-1",
	"ap-south-1",
	"ap-south-2",
	"ap-southeast-1",
	"ap-southeast-2",
	"ap-southeast-3",
	"ap-southeast-4",
	"ap-southeast-5",
	"ap-southeast-7",
	"ap-northeast-1",
	"ap-northeast-2",
	"ap-northeast-3"
]

export function emptyForm(provider: CloudProvider = "aws"): AccountForm {
	return {
		name: "",
		provider,
		auth_method: AUTH_METHODS[provider][0] as CloudAuthMethod,
		role_arn: "",
		regions: [],
		tenant_id: "",
		client_id: "",
		subscription_ids: [],
		tenant_domain: "",
		project_ids: [],
		excluded_project_ids: [],
		organization_id: "",
		excluded_checks: [],
		excluded_services: [],
		timeout_minutes: null,
		access_key_id: "",
		secret_access_key: "",
		client_secret: "",
		gcp_key_text: "",
		use_host_identity: false,
		secret_expires_at: null,
		enabled: true,
		schedule: "off",
		schedule_hour: 2,
		schedule_weekday: 6
	}
}

/**
 * An expiry is a calendar day: stored as the end of that day in UTC, shown by the date picker as
 * local midnight of the same day. Both directions read the day's numbers, so it never shifts a day
 * whatever the browser's time zone.
 */
export function pickerDay(iso: string): number {
	const stored = new Date(iso)
	return new Date(stored.getUTCFullYear(), stored.getUTCMonth(), stored.getUTCDate()).getTime()
}

/** The form for editing an account: its settings, and every credential field empty. */
export function formFromAccount(account: CloudAccount): AccountForm {
	const config = account.config ?? {}
	return {
		...emptyForm(account.provider),
		name: account.name,
		auth_method: account.auth_method,
		role_arn: config.role_arn ?? "",
		regions: [...(config.regions ?? [])],
		tenant_id: config.tenant_id ?? "",
		client_id: config.client_id ?? "",
		subscription_ids: [...(config.subscription_ids ?? [])],
		tenant_domain: config.tenant_domain ?? "",
		project_ids: [...(config.project_ids ?? [])],
		excluded_project_ids: [...(config.excluded_project_ids ?? [])],
		organization_id: config.organization_id ?? "",
		excluded_checks: [...(config.excluded_checks ?? [])],
		excluded_services: [...(config.excluded_services ?? [])],
		timeout_minutes: config.timeout_seconds ? Math.round(config.timeout_seconds / 60) : null,
		use_host_identity: account.auth_method === "role" && !account.secret_configured,
		secret_expires_at: account.secret_expires_at ? pickerDay(account.secret_expires_at) : null,
		enabled: account.enabled,
		schedule: account.schedule,
		schedule_hour: account.schedule_hour ?? 2,
		schedule_weekday: account.schedule_weekday ?? 6
	}
}

function trimmed(values: string[]): string[] {
	return [...new Set(values.map(value => value.trim()).filter(Boolean))]
}

/** The settings to send, for the form's provider only. */
export function configOf(form: AccountForm): CloudAccountConfigInput {
	const config: CloudAccountConfigInput = {
		excluded_checks: trimmed(form.excluded_checks),
		excluded_services: trimmed(form.excluded_services)
	}
	if (form.timeout_minutes) config.timeout_seconds = Math.round(form.timeout_minutes * 60)
	if (form.provider === "aws") {
		if (form.auth_method === "role") config.role_arn = form.role_arn.trim()
		const regions = trimmed(form.regions)
		if (regions.length) config.regions = regions
	} else if (form.provider === "azure" || form.provider === "m365") {
		config.tenant_id = form.tenant_id.trim()
		config.client_id = form.client_id.trim()
		if (form.provider === "azure") {
			const subscriptions = trimmed(form.subscription_ids)
			if (subscriptions.length) config.subscription_ids = subscriptions
		} else {
			config.tenant_domain = form.tenant_domain.trim()
		}
	} else {
		const projects = trimmed(form.project_ids)
		const excluded = trimmed(form.excluded_project_ids)
		if (projects.length) config.project_ids = projects
		if (excluded.length) config.excluded_project_ids = excluded
		if (form.organization_id.trim()) config.organization_id = form.organization_id.trim()
	}
	return config
}

/** A pasted GCP key file, parsed, or a reason it can't be. */
export function parseGcpKey(text: string): { key: Record<string, unknown> } | { problem: string } {
	let value: unknown
	try {
		value = JSON.parse(text)
	} catch {
		return { problem: "The key file isn't valid JSON." }
	}
	if (!value || typeof value !== "object" || Array.isArray(value)) return { problem: "The key file isn't a JSON object." }
	const key = value as Record<string, unknown>
	if (key.type !== "service_account") return { problem: "This isn't a service account key (its type isn't service_account)." }
	for (const field of ["project_id", "private_key_id", "private_key", "client_email", "client_id"]) {
		if (typeof key[field] !== "string" || !key[field]) return { problem: `The key file has no ${field}.` }
	}
	return { key }
}

/** Whether the form holds a credential to send (any of its fields filled in). */
export function credentialEntered(form: AccountForm): boolean {
	if (form.provider === "aws") return !!(form.access_key_id.trim() || form.secret_access_key.trim())
	if (form.provider === "gcp") return !!form.gcp_key_text.trim()
	return !!form.client_secret.trim()
}

/** The credential to send, or undefined to send none (an edit then keeps the stored one). */
export function secretOf(form: AccountForm): CloudAccountSecret | undefined {
	if (!credentialEntered(form)) return undefined
	if (form.provider === "aws") {
		return { access_key_id: form.access_key_id.trim(), secret_access_key: form.secret_access_key.trim() }
	}
	if (form.provider === "gcp") {
		const parsed = parseGcpKey(form.gcp_key_text)
		return "key" in parsed ? { service_account_key: parsed.key } : undefined
	}
	return { client_secret: form.client_secret.trim() }
}

function expiryOf(form: AccountForm): string | null {
	if (form.secret_expires_at === null) return null
	// The end of the picked day, in UTC: a secret valid "until the 31st" is valid all day.
	const day = new Date(form.secret_expires_at)
	return new Date(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate(), 23, 59, 59)).toISOString()
}

function scheduleOf(form: AccountForm): Pick<CloudAccountCreatePayload, "schedule" | "schedule_hour" | "schedule_weekday"> {
	if (form.schedule === "off") return { schedule: "off", schedule_hour: null, schedule_weekday: null }
	return {
		schedule: form.schedule,
		schedule_hour: form.schedule_hour,
		schedule_weekday: form.schedule === "weekly" ? form.schedule_weekday : null
	}
}

/** What's wrong with the form before it's sent, per field; empty when it can be saved. */
export function formProblems(form: AccountForm, editing: CloudAccount | null): Record<string, string> {
	const problems: Record<string, string> = {}
	if (!form.name.trim()) problems.name = "Enter a name."
	const entered = credentialEntered(form)
	// A credential is needed unless an AWS role is assumed with CoPilot's host identity, or an edit
	// keeps the stored one (a role account moving off the host identity has none stored).
	const hostIdentity = form.provider === "aws" && form.auth_method === "role" && form.use_host_identity
	const needsCredential = !hostIdentity && !editing?.secret_configured
	if (form.provider === "aws") {
		if (form.auth_method === "role" && !ROLE_ARN.test(form.role_arn.trim())) {
			problems.role_arn = "Enter the role's ARN, for example arn:aws:iam::123456789012:role/ProwlerScan."
		}
		const badRegion = trimmed(form.regions).find(region => !AWS_REGION.test(region))
		if (badRegion) problems.regions = `"${badRegion}" isn't an AWS region name.`
		const keyWanted = form.auth_method === "access_keys" || !form.use_host_identity
		if (keyWanted && (entered || needsCredential)) {
			if (!AWS_KEY_ID.test(form.access_key_id.trim())) {
				problems.access_key_id = "Enter a long-lived access key id (AKIA followed by 16 letters and digits)."
			}
			if (form.secret_access_key.trim().length < 16) problems.secret_access_key = "Enter the secret access key."
		}
	} else if (form.provider === "azure" || form.provider === "m365") {
		if (!UUID.test(form.tenant_id.trim())) problems.tenant_id = "Enter the directory (tenant) id, a GUID."
		if (!UUID.test(form.client_id.trim())) problems.client_id = "Enter the application (client) id, a GUID."
		if (form.provider === "azure") {
			const bad = trimmed(form.subscription_ids).find(id => !UUID.test(id))
			if (bad) problems.subscription_ids = `"${bad}" isn't a subscription id (a GUID).`
		} else if (!DOMAIN.test(form.tenant_domain.trim())) {
			problems.tenant_domain = "Enter one of the tenant's domains, for example contoso.onmicrosoft.com."
		}
		if (needsCredential && !entered) problems.client_secret = "Enter the client secret."
	} else {
		const bad = [...trimmed(form.project_ids), ...trimmed(form.excluded_project_ids)].find(id => !GCP_PROJECT.test(id))
		if (bad) problems.project_ids = `"${bad}" isn't a project id.`
		if (form.organization_id.trim() && !/^\d{1,32}$/.test(form.organization_id.trim())) {
			problems.organization_id = "An organization id is a number."
		}
		if (entered) {
			const parsed = parseGcpKey(form.gcp_key_text)
			if ("problem" in parsed) problems.gcp_key_text = parsed.problem
		} else if (needsCredential) {
			problems.gcp_key_text = "Paste or upload the service account's key file."
		}
	}
	const badCheck = trimmed(form.excluded_checks).find(check => !CHECK_ID.test(check))
	if (badCheck) problems.excluded_checks = `"${badCheck}" isn't a Prowler check id.`
	const badService = trimmed(form.excluded_services).find(service => !SERVICE.test(service))
	if (badService) problems.excluded_services = `"${badService}" isn't a Prowler service name.`
	if (form.timeout_minutes !== null && (form.timeout_minutes < 5 || form.timeout_minutes > 720)) {
		problems.timeout_minutes = "Between 5 and 720 minutes."
	}
	return problems
}

export function createPayload(form: AccountForm): CloudAccountCreatePayload {
	const roleWithoutKeys = form.provider === "aws" && form.auth_method === "role" && form.use_host_identity
	return {
		name: form.name.trim(),
		provider: form.provider,
		auth_method: form.auth_method,
		config: configOf(form),
		secret: roleWithoutKeys ? null : (secretOf(form) ?? null),
		secret_expires_at: expiryOf(form),
		enabled: form.enabled,
		...scheduleOf(form)
	}
}

export function updatePayload(form: AccountForm, account: CloudAccount): CloudAccountUpdatePayload {
	const payload: CloudAccountUpdatePayload = {
		name: form.name.trim(),
		config: configOf(form),
		secret_expires_at: expiryOf(form),
		enabled: form.enabled,
		...scheduleOf(form)
	}
	const roleWithoutKeys = account.auth_method === "role" && form.use_host_identity
	if (roleWithoutKeys) {
		if (account.secret_configured) payload.remove_secret = true
	} else {
		const secret = secretOf(form)
		if (secret) payload.secret = secret
	}
	return payload
}
