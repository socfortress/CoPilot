import type { Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * File Analysis: the Content tab of a script made of one very long line (#1360).
 *
 * Obfuscated droppers are often a single line of 65,536+ characters ("ASCII text, with very
 * long lines, with no line terminators"). Highlighting one froze the page: language detection
 * and Shiki's tokenizer both slow down with the square of a line's length (about 90 s of main
 * thread for 70,000 characters), and Content is the tab such a result opens on. These specs run
 * the real highlighter in a real browser on such a result, and check that a sample's content is
 * shown as text: it is the attacker's file. `E2E_SHOTS=<dir>` saves a screenshot of each state.
 */

const JOB_ID = "job-1360"
const SHA = "1e1f0a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f"

/** The issue's shape: a 70,000-character one-line PowerShell script. */
const ONE_LINE_SCRIPT =
	`powershell -nop -w hidden -c "iex([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('${
	"QUJD".repeat(17_500)
	}')))"`

/** A sample that carries markup: shown, it must stay text. */
const MARKUP_SCRIPT = [
	"# dropper",
	'$u = "<img src=x onerror=\'window.__sampleMarkupRan = 1\'>"',
	"Invoke-WebRequest -Uri $u -OutFile $env:TEMP\\a.exe"
].join("\n")

function job() {
	return {
		job_id: JOB_ID,
		sha256: SHA,
		filename: "dropper.ps1",
		customer_code: "ACME",
		source: "upload",
		status: "done",
		static_status: "done",
		sandbox_enabled: false,
		hardened: true,
		verdict: "suspicious",
		created_at: "2026-11-20T10:00:00Z",
		updated_at: "2026-11-20T10:01:00Z",
		error: null
	}
}

function result(raw: string, deobfuscated: string) {
	return {
		job: job(),
		preview_urls: [],
		verdict_reason: "static inspection: obfuscated script",
		inspector: {
			sha256: SHA,
			filename: "dropper.ps1",
			customer_code: "ACME",
			filetype: "script",
			magic: "ASCII text, with very long lines (70100), with no line terminators",
			extension_mismatch: false,
			entropy: 4.1,
			hashes: { sha256: SHA, sha1: "a".repeat(40), md5: "b".repeat(32) },
			iocs: { urls: [], ips: [], domains: [] },
			previews: [],
			content: { raw, deobfuscated },
			flags: ["obfuscated_script"],
			analysis_incomplete: false,
			verdict_hint: "suspicious",
			hardened: true
		}
	}
}

function json(route: Route, body: unknown) {
	return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
}

async function serveAnalysis(page: Page, raw: string, deobfuscated: string) {
	await page.context().route(
		url => url.pathname === `/api/file-analysis/job/${JOB_ID}`,
		route => json(route, { success: true, message: "ok", job: job() })
	)
	await page.context().route(
		url => url.pathname === `/api/file-analysis/result/${JOB_ID}`,
		route => json(route, { success: true, message: "ok", result: result(raw, deobfuscated) })
	)
}

/** Records the longest task the page's main thread ran, from before the app boots. */
async function watchLongTasks(page: Page) {
	await page.addInitScript(() => {
		const w = window as unknown as { __longestTask: number }
		w.__longestTask = 0
		new PerformanceObserver(list => {
			for (const entry of list.getEntries()) w.__longestTask = Math.max(w.__longestTask, entry.duration)
		}).observe({ type: "longtask", buffered: true })
	})
}

async function shot(page: Page, name: string) {
	const dir = process.env.E2E_SHOTS
	if (!dir) return
	// Past the app's splash screen, which fades out over the first half second after a load.
	await page.waitForTimeout(1000)
	await page.screenshot({ path: `${dir}/${name}.png` })
}

test.beforeEach(async ({ context, page }) => {
	await installMockBackend(context)
	await signIn(page)
})

test("a one-line script of 70,000 characters leaves the page responsive", async ({ page }) => {
	await watchLongTasks(page)
	await serveAnalysis(page, ONE_LINE_SCRIPT, "iex $decoded")
	await page.goto(`/file-analysis/${JOB_ID}`)

	// Content is the tab this result opens on: no page previews for a script.
	await expect(page.getByText("Raw source")).toBeVisible()
	const raw = page.locator("pre").filter({ hasText: "FromBase64String" }).first()
	await expect(raw).toContainText("QUJDQUJD")

	// Give the highlighter time to run, then read the longest task it caused.
	await page.waitForTimeout(3000)
	const longest = await page.evaluate(() => (window as unknown as { __longestTask: number }).__longestTask)
	expect(longest, `the longest main-thread task was ${Math.round(longest)} ms`).toBeLessThan(1000)
	await shot(page, "file-analysis-one-line-script")

	// And the page still answers: another tab opens at once.
	await page.locator(".n-tabs-tab", { hasText: "Metadata" }).click()
	await expect(page.getByText("ASCII text, with very long lines (70100)")).toBeVisible({ timeout: 3000 })
})

test("a sample's content is shown as text, never run as markup", async ({ page }) => {
	await serveAnalysis(page, MARKUP_SCRIPT, MARKUP_SCRIPT)
	await page.goto(`/file-analysis/${JOB_ID}`)

	const raw = page.locator("pre").filter({ hasText: "Invoke-WebRequest" }).first()
	await expect(raw).toContainText("<img src=x onerror=")
	// An image that failed to load would have run its handler by now.
	await page.waitForTimeout(1500)
	expect(await page.evaluate(() => (window as unknown as { __sampleMarkupRan?: number }).__sampleMarkupRan)).toBeUndefined()
	await expect(page.locator(".n-card img")).toHaveCount(0)
})

test("a very large sample shows its start until Show all", async ({ page }) => {
	const huge = `${"A".repeat(250_000)} END-OF-SAMPLE`
	await serveAnalysis(page, huge, "")
	await page.goto(`/file-analysis/${JOB_ID}`)

	const cut = page.getByTestId("code-source-cut").first()
	await expect(cut).toContainText("Showing the first 200,000 of 250,014 characters.")
	await expect(page.locator("pre").filter({ hasText: "AAAA" }).first()).not.toContainText("END-OF-SAMPLE")
	await cut.scrollIntoViewIfNeeded()
	await shot(page, "file-analysis-large-sample")

	await cut.getByRole("button", { name: "Show all" }).click()
	await expect(page.locator("pre").filter({ hasText: "AAAA" }).first()).toContainText("END-OF-SAMPLE")
	await expect(page.getByTestId("code-source-cut")).toHaveCount(0)
})
