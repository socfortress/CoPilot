import type { Page, Route } from "@playwright/test"
import { readFile } from "node:fs/promises"
import { expect, test } from "@playwright/test"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * File Analysis: the CAPE report, read off the backend's event loop (#1361).
 *
 * The backend now summarises a report in a worker process, within limits (size, time). A
 * report it couldn't read says why on the Detonation tab, and can still be downloaded; the
 * raw report is saved exactly as CAPE wrote it, never parsed and re-indented in the page (it
 * runs to tens of MB). `E2E_SHOTS=<dir>` saves a screenshot of each state.
 */

const JOB_ID = "job-1361"
const SHA = "2b1f0a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f"
const REASON = "The CAPE report is larger than CoPilot reads (256 MB, CAPE_REPORT_MAX_MB)."
// As CAPE wrote it: compact, with spacing the page must keep.
const RAW_REPORT = '{"info":{"id":77},"behavior":{"processes":[]},   "malscore":9.4}'

function job(extra: Record<string, unknown>) {
	return {
		job_id: JOB_ID,
		sha256: SHA,
		filename: "loader.exe",
		customer_code: "ACME",
		source: "upload",
		status: "done",
		static_status: "done",
		sandbox_enabled: true,
		hardened: true,
		verdict: "suspicious",
		created_at: "2026-11-21T10:00:00Z",
		updated_at: "2026-11-21T10:05:00Z",
		error: null,
		...extra
	}
}

function result(jobBody: Record<string, unknown>, sandbox: Record<string, unknown> | null) {
	return {
		job: jobBody,
		preview_urls: [],
		verdict_reason: "static inspection: packed executable",
		inspector: {
			sha256: SHA,
			filename: "loader.exe",
			customer_code: "ACME",
			filetype: "pe",
			magic: "PE32+ executable (GUI) x86-64, for MS Windows",
			extension_mismatch: false,
			entropy: 7.2,
			hashes: { sha256: SHA, sha1: "a".repeat(40), md5: "b".repeat(32) },
			iocs: { urls: [], ips: [], domains: [] },
			previews: [],
			content: {},
			flags: ["packed"],
			analysis_incomplete: false,
			verdict_hint: "suspicious",
			hardened: true
		},
		sandbox
	}
}

function json(route: Route, body: unknown) {
	return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
}

async function serveAnalysis(page: Page, jobBody: Record<string, unknown>, sandbox: Record<string, unknown> | null) {
	await page.context().route(
		url => url.pathname === `/api/file-analysis/job/${JOB_ID}`,
		route => json(route, { success: true, message: "ok", job: jobBody })
	)
	await page.context().route(
		url => url.pathname === `/api/file-analysis/result/${JOB_ID}`,
		route => json(route, { success: true, message: "ok", result: result(jobBody, sandbox) })
	)
	await page.context().route(
		url => url.pathname === `/api/file-analysis/result/${JOB_ID}/cape-report`,
		route =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				headers: { "Content-Disposition": `attachment; filename="cape-report-${JOB_ID}.json"` },
				body: RAW_REPORT
			})
	)
}

async function openDetonation(page: Page) {
	await page.goto(`/file-analysis/${JOB_ID}`)
	await page.locator(".n-tabs-tab", { hasText: "Detonation" }).click()
}

async function downloadedText(page: Page, click: () => Promise<void>) {
	const [download] = await Promise.all([page.waitForEvent("download"), click()])
	const path = await download.path()
	return { name: download.suggestedFilename(), text: await readFile(path, "utf-8") }
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

test("a report CoPilot couldn't read says why, and downloads as CAPE wrote it", async ({ page }) => {
	await serveAnalysis(page, job({ dynamic_status: "failed", dynamic_task_id: "77", dynamic_error: REASON }), null)
	await openDetonation(page)

	const failure = page.getByTestId("detonation-report-error")
	await expect(failure).toContainText("The sandbox ran, but CoPilot couldn't use its report.")
	await expect(failure).toContainText(REASON)
	await expect(page.getByText("platform mismatch")).toHaveCount(0)
	await shot(page, "file-analysis-report-unreadable")

	const file = await downloadedText(page, () => failure.getByRole("button", { name: "Download the raw CAPE report" }).click())
	expect(file.name).toBe(`cape-report-${JOB_ID}.json`)
	expect(file.text).toBe(RAW_REPORT)
})

test("a summarised detonation's raw report is saved unchanged", async ({ page }) => {
	const sandbox = {
		task_id: 77,
		malscore: 4.5,
		family: "",
		verdict: "suspicious",
		signatures: [{ name: "packer_entropy", description: "High entropy section", severity: 2, noise: false, low_confidence: true, mitre: [] }],
		c2_ips: [],
		c2_domains: [],
		dropped: [],
		screenshots: [],
		duration: 120,
		machine: "capewin (windows)",
		package: "exe",
		processes: [{ name: "loader.exe", pid: 4242, ppid: 100, command_line: "C:\\Temp\\loader.exe" }],
		hosts: [],
		domains: [],
		dns: [],
		http: [],
		connections: [],
		ttps: [],
		payloads: [],
		errors: [],
		behavior: { files: ["C:\\Users\\cape\\AppData\\Local\\Temp\\loader.tmp"] },
		enhanced: [],
		dead_hosts: []
	}
	await serveAnalysis(page, job({ dynamic_status: "done", dynamic_task_id: "77" }), sandbox)
	await openDetonation(page)

	const raw = page.getByRole("button", { name: "Raw CAPE JSON (advanced)" })
	await expect(raw).toBeVisible()
	const file = await downloadedText(page, () => raw.click())
	expect(file.text).toBe(RAW_REPORT)
})
