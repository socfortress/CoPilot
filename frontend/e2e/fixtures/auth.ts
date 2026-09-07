import type { Page } from "@playwright/test"
import { expect } from "@playwright/test"
import { API_BASE, SEED_PASSWORD } from "../seed"

/** Tokens captured during sign-in, keyed by username. */
const tokens = new Map<string, string>()

/**
 * Signs in through the real login form rather than by injecting a token.
 *
 * The app derives the caller's role from the JWT's `scopes` claim client-side, so a
 * hand-planted token would also plant the role — and a tenancy test that decides for
 * itself who the user is has stopped testing anything. Going through the form means
 * the browser holds exactly what the backend issued.
 *
 * The token is captured off the `/auth/token` response on the way past: the app
 * persists it through secure-ls (AES), so it cannot be read back out of storage.
 */
export async function signIn(page: Page, username: string, password: string = SEED_PASSWORD) {
	await page.goto("/login")

	const tokenResponse = page.waitForResponse(res => res.url().includes("/auth/token") && res.request().method() === "POST")

	await page.getByPlaceholder("Insert your username").fill(username)
	await page.getByPlaceholder("Insert your password").fill(password)
	await page.getByRole("button", { name: /sign in with password/i }).click()

	const body = (await (await tokenResponse).json()) as { access_token?: string }
	if (!body.access_token) {
		throw new Error(`sign-in for "${username}" returned no access_token (2FA enabled on this account?)`)
	}
	tokens.set(username, body.access_token)

	// The app redirects "/" -> "/overview" once the token is stored.
	await expect(page).toHaveURL(/\/overview/, { timeout: 30_000 })
}

export async function signOut(page: Page) {
	// Clearing storage is enough: the session lives in a persisted Pinia store, and
	// going through the profile menu would couple every spec to that menu's markup.
	await page.goto("/login")
	await page.evaluate(() => {
		localStorage.clear()
		sessionStorage.clear()
	})
}

/**
 * Calls the backend directly with the token this user signed in with.
 *
 * Hiding a customer from a list is not the same as refusing to serve it, and the
 * difference is only visible below the UI: the specs use this to ask the API for
 * another tenant's data the way a curious analyst with devtools would.
 */
export async function apiAs(username: string, path: string, init: RequestInit = {}) {
	const token = tokens.get(username)
	if (!token) {
		throw new Error(`no token for "${username}" — call signIn() first`)
	}
	return fetch(`${API_BASE}${path}`, {
		...init,
		headers: {
			Authorization: `Bearer ${token}`,
			...(init.body ? { "Content-Type": "application/json" } : {}),
			...(init.headers ?? {})
		}
	})
}
