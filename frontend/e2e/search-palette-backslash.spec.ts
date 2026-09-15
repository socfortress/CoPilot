import { expect, test } from "@playwright/test"
import { signIn, signOut } from "./fixtures/auth"
import { UNSCOPED_ANALYST } from "./seed"

/**
 * #1133 — a `C:\` search in the Ctrl+K palette logged the user out.
 *
 * The alerts provider put the query into a path segment unencoded; the browser
 * rewrote the backslash into a slash, the backend redirected, the redirected
 * request lost its token, and the resulting 401 was treated as an expired session.
 * This drives the real palette against the real backend on purpose: the bug lived
 * in the hand-off between browser URL parsing, nginx/Starlette and the interceptor,
 * none of which an API mock would exercise.
 */

test.describe("global search with a backslash in the term", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, UNSCOPED_ANALYST)
	})

	test("sends the term as one encoded path segment and keeps the session", async ({ page }) => {
		await page.goto("/overview")

		const titleSearch = page.waitForRequest(req => req.url().includes("/incidents/db_operations/alerts/title/"))

		await page
			.getByRole("button", { name: /search/i })
			.first()
			.click()
		const input = page.getByPlaceholder("Search")
		await expect(input).toBeVisible()
		// `openBox` clears the field 100 ms after showing the modal; typing before that
		// tick is silently wiped, so let it pass before entering the term.
		await page.waitForTimeout(250)
		await input.fill("C:\\")
		await expect(input).toHaveValue("C:\\")

		const request = await titleSearch
		expect(new URL(request.url()).pathname).toMatch(/\/alerts\/title\/C%3A%5C$/)

		const response = await request.response()
		expect(response?.status()).toBe(200)

		// The palette is still open, the term is still there, and nobody was sent to /login.
		await expect(input).toHaveValue("C:\\")
		await expect(page).not.toHaveURL(/\/(login|logout)/)
	})
})
