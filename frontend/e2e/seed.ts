import fs from "node:fs"
import path from "node:path"
import process from "node:process"
import { fileURLToPath } from "node:url"
import "./load-env"

/**
 * Seeds the tenants and users the tenancy specs need, straight through the public API
 * as an admin. Deliberately not a DB fixture: the assignment flow
 * (Users → Assign Customer) is itself what #1050 was about, so exercising it here
 * means a broken assignment endpoint fails the suite instead of quietly producing a
 * "correctly" scoped analyst.
 *
 * Everything is idempotent — reruns reuse what is already there.
 */

/** Origin the backend is served from. */
export const API_ORIGIN = process.env.E2E_API_URL ?? "http://127.0.0.1:5000"
/** Every CoPilot route lives under /api — the same prefix Vite proxies to. */
export const API_BASE = `${API_ORIGIN}/api`

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? "admin"
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin"

/** Password shared by the seeded analysts — matches the backend's complexity rule. */
export const SEED_PASSWORD = "E2ePlaywr1ght!"

/** Analyst assigned to one tenant — the reporter's account in #1050. */
export const SCOPED_ANALYST = "e2e_pw_scoped_analyst"
/** Analyst with no assignment at all — still deployment-wide, by design. */
export const UNSCOPED_ANALYST = "e2e_pw_unscoped_analyst"

/** Tenants the specs would like to own, when the deployment lets us create them. */
const PREFERRED = [
	{ code: "E2E_PWA", name: "E2E Playwright Alpha" },
	{ code: "E2E_PWB", name: "E2E Playwright Beta" }
]

export interface Tenant {
	code: string
	name: string
}

const TENANTS_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), ".tenants.json")

/**
 * The two tenants this run is using.
 *
 * Resolved by `seed()` and written to disk, because Playwright runs globalSetup in a
 * different process from the specs. Which two they are is not fixed: an unlicensed
 * deployment refuses to create a second customer, so the suite falls back to whatever
 * the deployment already has (see `resolveTenants`).
 */
export function tenants(): [Tenant, Tenant] {
	if (!fs.existsSync(TENANTS_FILE)) {
		throw new Error(`${TENANTS_FILE} is missing — globalSetup did not run, or it failed before seeding.`)
	}
	return JSON.parse(fs.readFileSync(TENANTS_FILE, "utf-8")) as [Tenant, Tenant]
}

async function api(path: string, init: RequestInit = {}, token?: string) {
	return fetch(`${API_BASE}${path}`, {
		...init,
		headers: {
			...(init.body && !(init.body instanceof URLSearchParams) ? { "Content-Type": "application/json" } : {}),
			...(token ? { Authorization: `Bearer ${token}` } : {}),
			...(init.headers ?? {})
		}
	})
}

export async function login(username: string, password: string): Promise<string> {
	const res = await api("/auth/token", { method: "POST", body: new URLSearchParams({ username, password }) })
	if (!res.ok) {
		throw new Error(`login failed for "${username}" (${res.status}): ${await res.text()}`)
	}
	const body = (await res.json()) as { access_token?: string }
	if (!body.access_token) {
		// By far the most likely cause, and worth naming rather than leaving as "undefined".
		throw new Error(`login for "${username}" returned no access_token — if this account has 2FA enabled, seed with one that does not.`)
	}
	return body.access_token
}

async function listCustomers(token: string): Promise<Tenant[]> {
	const res = await api("/customers", {}, token)
	if (!res.ok) {
		throw new Error(`could not list customers (${res.status}): ${await res.text()}`)
	}
	const body = (await res.json()) as { customers?: { customer_code: string; customer_name: string }[] }
	return (body.customers ?? []).map(c => ({ code: c.customer_code, name: c.customer_name }))
}

/** Tries to create a customer. Returns false when the deployment refuses (e.g. licensing). */
async function tryCreateCustomer(token: string, tenant: Tenant): Promise<boolean> {
	const res = await api(
		"/customers",
		{
			method: "POST",
			body: JSON.stringify({
				customer_code: tenant.code,
				customer_name: tenant.name,
				contact_first_name: "E2E",
				contact_last_name: "Playwright",
				phone: "000",
				address_line1: "1 Test Street",
				city: "Testville",
				state: "TS",
				postal_code: "00000",
				country: "IT",
				customer_type: "MSSP"
			})
		},
		token
	)
	// 400 == "already exists", which is a successful outcome for a seed.
	return res.ok || res.status === 400
}

/**
 * Picks the two tenants the specs will compare.
 *
 * A licensed deployment lets the suite create its own, which keeps it self-contained.
 * An unlicensed one caps the customer count, so rather than failing, the suite borrows
 * two customers that already exist — it only ever *reads* them, and the analyst it
 * assigns is one it created itself.
 */
async function resolveTenants(token: string): Promise<[Tenant, Tenant]> {
	const existing = await listCustomers(token)
	const resolved: Tenant[] = []

	for (const wanted of PREFERRED) {
		const already = existing.find(c => c.code === wanted.code)
		if (already) {
			resolved.push(already)
		} else if (await tryCreateCustomer(token, wanted)) {
			resolved.push(wanted)
		}
	}

	// Top up from whatever the deployment already has, skipping ones we already picked.
	for (const candidate of existing) {
		if (resolved.length >= 2) break
		if (!resolved.some(t => t.code === candidate.code)) {
			resolved.push(candidate)
		}
	}

	if (resolved.length < 2) {
		throw new Error(
			`These tests compare one tenant against another, so the deployment needs at least two customers.\n` +
				`It has ${existing.length}, and creating more was refused (an unlicensed CoPilot allows only one).\n\n` +
				`Create a second customer by hand, or install a license, then rerun.`
		)
	}

	return [resolved[0], resolved[1]]
}

async function ensureAnalyst(token: string, username: string) {
	const res = await api(
		"/auth/register",
		{
			method: "POST",
			body: JSON.stringify({ username, password: SEED_PASSWORD, email: `${username}@e2e.example`, role_id: 2 })
		},
		token
	)
	if (!res.ok && res.status !== 400) {
		throw new Error(`could not create user ${username} (${res.status}): ${await res.text()}`)
	}
}

async function userIdOf(token: string, username: string): Promise<number> {
	const res = await api("/auth/users", {}, token)
	if (!res.ok) {
		throw new Error(`could not list users (${res.status}): ${await res.text()}`)
	}
	const body = (await res.json()) as { users?: { id: number; username: string }[] }
	const user = body.users?.find(u => u.username === username)
	if (!user) {
		throw new Error(`user ${username} not found after creating it`)
	}
	return user.id
}

async function assignCustomers(token: string, userId: number, codes: string[]) {
	const res = await api(`/auth/users/${userId}/customers`, { method: "POST", body: JSON.stringify(codes) }, token)
	if (!res.ok) {
		throw new Error(`could not assign [${codes.join(", ")}] to user ${userId} (${res.status}): ${await res.text()}`)
	}
}

export async function seed(): Promise<[Tenant, Tenant]> {
	let adminToken: string
	try {
		adminToken = await login(ADMIN_USER, ADMIN_PASSWORD)
	} catch (err) {
		throw new Error(
			`Could not authenticate as "${ADMIN_USER}" against ${API_BASE}.\n\n` +
				`The admin password is generated on the backend's FIRST boot and only ever printed\n` +
				`to its log — look for "Admin user password:" — so it has to be passed in here:\n\n` +
				`  E2E_ADMIN_PASSWORD='<that password>' pnpm test:e2e\n\n` +
				`Backend not running at all? cd backend && uvicorn copilot:app --port 5000\n\n${(err as Error).message}`
		)
	}

	const resolved = await resolveTenants(adminToken)

	await ensureAnalyst(adminToken, SCOPED_ANALYST)
	await ensureAnalyst(adminToken, UNSCOPED_ANALYST)

	// The whole point: one analyst assigned to exactly one tenant...
	await assignCustomers(adminToken, await userIdOf(adminToken, SCOPED_ANALYST), [resolved[0].code])
	// ...and one assigned to none, which still means deployment-wide (#1050's upgrade
	// compromise). Both halves have to be seeded or the specs prove only half the rule.
	await assignCustomers(adminToken, await userIdOf(adminToken, UNSCOPED_ANALYST), [])

	fs.writeFileSync(TENANTS_FILE, JSON.stringify(resolved, null, 2))
	return resolved
}
