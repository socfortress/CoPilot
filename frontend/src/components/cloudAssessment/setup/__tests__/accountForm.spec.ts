import type { AccountForm } from "../accountForm"
import type { CloudAccount } from "@/types/cloud-assessment"
import { describe, expect, it } from "vitest"
import { configOf, createPayload, emptyForm, formFromAccount, formProblems, parseGcpKey, pickerDay, updatePayload } from "../accountForm"

const TENANT = "11111111-2222-3333-4444-555555555555"
const CLIENT = "66666666-7777-8888-9999-000000000000"
// AWS's documented example keys: placeholders, never a real credential.
const KEY_ID = "AKIAIOSFODNN7EXAMPLE"
const KEY_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
const PEM = `-----BEGIN PRIVATE KEY-----\n${"A".repeat(120)}\n-----END PRIVATE KEY-----\n`

function form(overrides: Partial<AccountForm> = {}): AccountForm {
	return { ...emptyForm(overrides.provider ?? "aws"), name: "Production", ...overrides }
}

function stored(overrides: Partial<CloudAccount> = {}): CloudAccount {
	return {
		id: 9,
		customer_code: "ACME",
		name: "Production",
		provider: "aws",
		auth_method: "role",
		config: { role_arn: "arn:aws:iam::123456789012:role/ProwlerScan", regions: ["eu-west-1"], timeout_seconds: 5400 },
		cloud_account: "123456789012",
		external_id: "copilot-0123456789abcdef0123456789abcdef",
		secret_configured: true,
		secret_hint: "…MPLE",
		secret_expires_at: null,
		secret_expires_in_days: null,
		enabled: true,
		schedule: "weekly",
		schedule_hour: 3,
		schedule_weekday: 2,
		next_scheduled_at: null,
		last_connection_test_at: null,
		last_connection_ok: null,
		last_connection_error: null,
		last_connection_message: null,
		created_by: null,
		created_at: null,
		updated_by: null,
		updated_at: null,
		last_scan: null,
		last_completed_scan: null,
		...overrides
	}
}

function gcpKey(overrides: Record<string, unknown> = {}): string {
	return JSON.stringify({
		type: "service_account",
		project_id: "acme-prod-1234",
		private_key_id: "0123456789abcdef0123456789abcdef01234567",
		private_key: PEM,
		client_email: "prowler@acme-prod-1234.iam.gserviceaccount.com",
		client_id: "123456789012345678901",
		...overrides
	})
}

describe("an AWS role", () => {
	const arn = "arn:aws:iam::123456789012:role/ProwlerScan"

	it("assumed with CoPilot's host identity needs no key and sends no credential", () => {
		const f = form({ auth_method: "role", role_arn: arn, use_host_identity: true, regions: [" eu-west-1 ", "eu-west-1"] })
		expect(formProblems(f, null)).toEqual({})
		const payload = createPayload(f)
		expect(payload.secret).toBeNull()
		expect(payload.config).toEqual({ role_arn: arn, regions: ["eu-west-1"], excluded_checks: [], excluded_services: [] })
	})

	it("refuses an ARN that isn't a role's, and a region that isn't one", () => {
		const problems = formProblems(form({ auth_method: "role", role_arn: "arn:aws:iam::12345:user/x", regions: ["Europe"], use_host_identity: true }), null)
		expect(Object.keys(problems).sort()).toEqual(["regions", "role_arn"])
	})

	it("assumed with an IAM user's keys needs a long-lived key", () => {
		const f = form({ auth_method: "role", role_arn: arn, access_key_id: "ASIAIOSFODNN7EXAMPLE", secret_access_key: KEY_SECRET })
		expect(formProblems(f, null)).toHaveProperty("access_key_id")
		const good = { ...f, access_key_id: KEY_ID }
		expect(formProblems(good, null)).toEqual({})
		expect(createPayload(good).secret).toEqual({ access_key_id: KEY_ID, secret_access_key: KEY_SECRET })
	})

	it("edited without touching the keys keeps them: nothing is sent", () => {
		const account = stored()
		const f = formFromAccount(account)
		expect(f.access_key_id).toBe("")
		expect(f.secret_access_key).toBe("")
		expect(formProblems(f, account)).toEqual({})
		const payload = updatePayload(f, account)
		expect(payload).not.toHaveProperty("secret")
		expect(payload).not.toHaveProperty("remove_secret")
		expect(payload.config?.timeout_seconds).toBe(5400)
	})

	it("moved to CoPilot's host identity removes the stored keys", () => {
		const account = stored()
		const payload = updatePayload({ ...formFromAccount(account), use_host_identity: true }, account)
		expect(payload.remove_secret).toBe(true)
		expect(payload).not.toHaveProperty("secret")
	})

	it("already on the host identity sends no removal", () => {
		const account = stored({ secret_configured: false, secret_hint: null })
		const f = formFromAccount(account)
		expect(f.use_host_identity).toBe(true)
		expect(updatePayload(f, account)).not.toHaveProperty("remove_secret")
	})

	it("moved off the host identity needs keys, since none are stored", () => {
		const account = stored({ secret_configured: false, secret_hint: null })
		const f = { ...formFromAccount(account), use_host_identity: false }
		expect(Object.keys(formProblems(f, account)).sort()).toEqual(["access_key_id", "secret_access_key"])
	})
})

describe("aWS access keys", () => {
	it("are required to add the account", () => {
		expect(Object.keys(formProblems(form({ auth_method: "access_keys" }), null)).sort()).toEqual(["access_key_id", "secret_access_key"])
	})

	it("send no role and no Azure or GCP setting", () => {
		const config = configOf(form({ auth_method: "access_keys", role_arn: "arn:aws:iam::123456789012:role/x", tenant_id: TENANT }))
		expect(config).toEqual({ excluded_checks: [], excluded_services: [] })
	})
})

describe("azure and Microsoft 365", () => {
	it("check the tenant, the app, the subscriptions and the secret", () => {
		const problems = formProblems(form({ provider: "azure", tenant_id: "acme", client_id: CLIENT, subscription_ids: ["sub-1"] }), null)
		expect(Object.keys(problems).sort()).toEqual(["client_secret", "subscription_ids", "tenant_id"])
	})

	it("send the tenant, the app and the subscriptions for Azure, never a tenant domain", () => {
		const f = form({ provider: "azure", tenant_id: TENANT, client_id: CLIENT, subscription_ids: [TENANT], tenant_domain: "x.com", client_secret: "abc~secret" })
		expect(formProblems(f, null)).toEqual({})
		const payload = createPayload(f)
		expect(payload.config).toEqual({ tenant_id: TENANT, client_id: CLIENT, subscription_ids: [TENANT], excluded_checks: [], excluded_services: [] })
		expect(payload.secret).toEqual({ client_secret: "abc~secret" })
	})

	it("need one of the tenant's domains for Microsoft 365", () => {
		const f = form({ provider: "m365", tenant_id: TENANT, client_id: CLIENT, client_secret: "abc~secret" })
		expect(formProblems(f, null)).toHaveProperty("tenant_domain")
		const good = { ...f, tenant_domain: "contoso.onmicrosoft.com" }
		expect(formProblems(good, null)).toEqual({})
		expect(createPayload(good).config.tenant_domain).toBe("contoso.onmicrosoft.com")
		expect(createPayload(good).config).not.toHaveProperty("subscription_ids")
	})

	it("keep the stored client secret when the field is left blank", () => {
		const account = stored({ provider: "azure", auth_method: "client_secret", config: { tenant_id: TENANT, client_id: CLIENT } })
		const f = formFromAccount(account)
		expect(formProblems(f, account)).toEqual({})
		expect(updatePayload(f, account)).not.toHaveProperty("secret")
	})
})

describe("a client secret's expiry", () => {
	it("is the end of the picked day in UTC, and reads back as the same day", () => {
		const picked = new Date(2026, 11, 31).getTime() // local midnight, as the date picker gives it
		const f = form({ provider: "azure", tenant_id: TENANT, client_id: CLIENT, client_secret: "abc~secret", secret_expires_at: picked })
		const sent = createPayload(f).secret_expires_at
		expect(sent).toBe("2026-12-31T23:59:59.000Z")
		expect(pickerDay(sent as string)).toBe(picked)
	})

	it("is null when none is picked", () => {
		expect(createPayload(form({ auth_method: "role", use_host_identity: true })).secret_expires_at).toBeNull()
	})
})

describe("a GCP service account key", () => {
	it("is read from its JSON", () => {
		expect(parseGcpKey(gcpKey())).toHaveProperty("key")
		expect(parseGcpKey("{not json")).toEqual({ problem: "The key file isn't valid JSON." })
		expect(parseGcpKey("[1]")).toEqual({ problem: "The key file isn't a JSON object." })
		expect(parseGcpKey(gcpKey({ type: "authorized_user" }))).toHaveProperty("problem")
		expect(parseGcpKey(gcpKey({ private_key: "" }))).toEqual({ problem: "The key file has no private_key." })
	})

	it("is required to add the account, and checked when pasted", () => {
		expect(formProblems(form({ provider: "gcp" }), null)).toHaveProperty("gcp_key_text")
		expect(formProblems(form({ provider: "gcp", gcp_key_text: "{}" }), null).gcp_key_text).toContain("service account")
		const f = form({ provider: "gcp", gcp_key_text: gcpKey(), project_ids: ["acme-prod-1234"], organization_id: "1234567890" })
		expect(formProblems(f, null)).toEqual({})
		const payload = createPayload(f)
		expect(payload.secret?.service_account_key).toMatchObject({ type: "service_account", project_id: "acme-prod-1234" })
		expect(payload.config).toEqual({ project_ids: ["acme-prod-1234"], organization_id: "1234567890", excluded_checks: [], excluded_services: [] })
	})

	it("checks project and organization ids", () => {
		const problems = formProblems(form({ provider: "gcp", gcp_key_text: gcpKey(), project_ids: ["Acme Prod"], organization_id: "org-1" }), null)
		expect(Object.keys(problems).sort()).toEqual(["organization_id", "project_ids"])
	})
})

describe("scan options and the schedule", () => {
	const base = { auth_method: "role" as const, role_arn: "arn:aws:iam::123456789012:role/ProwlerScan", use_host_identity: true }

	it("check Prowler's check ids and service names, and send them trimmed once", () => {
		expect(formProblems(form({ ...base, excluded_checks: ["Not A Check"] }), null)).toHaveProperty("excluded_checks")
		expect(formProblems(form({ ...base, excluded_services: ["s3 buckets"] }), null)).toHaveProperty("excluded_services")
		const config = configOf(form({ ...base, excluded_checks: [" iam_root_mfa_enabled", "iam_root_mfa_enabled"], excluded_services: ["s3"] }))
		expect(config.excluded_checks).toEqual(["iam_root_mfa_enabled"])
		expect(config.excluded_services).toEqual(["s3"])
	})

	it("bound the timeout to what the backend takes, 5 to 720 minutes", () => {
		expect(formProblems(form({ ...base, timeout_minutes: 4 }), null)).toHaveProperty("timeout_minutes")
		expect(formProblems(form({ ...base, timeout_minutes: 721 }), null)).toHaveProperty("timeout_minutes")
		expect(formProblems(form({ ...base, timeout_minutes: 5 }), null)).toEqual({})
		expect(configOf(form({ ...base, timeout_minutes: 90 })).timeout_seconds).toBe(5400)
		expect(configOf(form(base))).not.toHaveProperty("timeout_seconds")
	})

	it("send only the parts of the schedule that apply", () => {
		expect(createPayload(form({ ...base, schedule: "off" }))).toMatchObject({ schedule: "off", schedule_hour: null, schedule_weekday: null })
		expect(createPayload(form({ ...base, schedule: "daily", schedule_hour: 4 }))).toMatchObject({ schedule_hour: 4, schedule_weekday: null })
		expect(createPayload(form({ ...base, schedule: "weekly", schedule_hour: 4, schedule_weekday: 0 }))).toMatchObject({
			schedule_hour: 4,
			schedule_weekday: 0
		})
	})

	it("need a name", () => {
		expect(formProblems(form({ ...base, name: "  " }), null)).toEqual({ name: "Enter a name." })
	})
})
