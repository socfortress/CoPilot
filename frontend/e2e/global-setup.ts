import process from "node:process"
import { BASE_URL } from "./config"
import { API_ORIGIN, login, seed } from "./seed"

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? "admin"
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin"

/**
 * Runs once before the suite. Fails loudly and with instructions when something is not
 * where it should be — an e2e suite that silently skips is worse than one that does not
 * exist, and one that silently tests the *wrong backend* is worse than both.
 */
export default async function globalSetup() {
	try {
		const ping = await fetch(`${API_ORIGIN}/openapi.json`)
		if (!ping.ok) {
			throw new Error(`unexpected status ${ping.status}`)
		}
	} catch (err) {
		throw new Error(
			`CoPilot backend is not reachable at ${API_ORIGIN}.\n\n` +
				`  1. docker compose up -d copilot-mysql copilot-minio\n` +
				`  2. cd backend && uvicorn copilot:app --port 5000\n\n` +
				`Override the address with E2E_API_URL.\n\nCause: ${(err as Error).message}`
		)
	}

	await seed()
	await assertFrontendTalksToSeededBackend()
}

/**
 * Checks that the app under test proxies to the backend we just seeded.
 *
 * Vite proxies `/api` to whatever `VITE_API_URL` said *when it started*, and the config
 * reuses an already-running dev server. So a `pnpm dev` left over from ordinary work
 * happily serves the app while sending its API calls to a different CoPilot — every
 * spec then fails at sign-in with an unhelpful "no access_token", and the tenancy
 * results, if any came back, would be about the wrong deployment entirely.
 */
async function assertFrontendTalksToSeededBackend() {
	// Prove the credential works against the backend directly first, so a failure
	// through the proxy can only mean the proxy points elsewhere.
	await login(ADMIN_USER, ADMIN_PASSWORD)

	const res = await fetch(`${BASE_URL}/api/auth/token`, {
		method: "POST",
		body: new URLSearchParams({ username: ADMIN_USER, password: ADMIN_PASSWORD })
	}).catch(err => {
		throw new Error(`Frontend at ${BASE_URL} is not reachable: ${(err as Error).message}`)
	})

	if (!res.ok) {
		throw new Error(
			`The app at ${BASE_URL} is NOT talking to the backend at ${API_ORIGIN}.\n\n` +
				`The same admin credential works against the backend directly but is rejected (${res.status})\n` +
				`through the app's /api proxy, which means Vite is forwarding somewhere else.\n\n` +
				`Almost always: a "pnpm dev" is already running on that port from earlier work, started with a\n` +
				`different VITE_API_URL, and Playwright reused it. Either stop it, or run the suite on its own\n` +
				`port:\n\n  E2E_PORT=5199 pnpm test:e2e\n`
		)
	}
}
