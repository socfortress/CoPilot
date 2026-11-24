import type { BrowserContext, Route } from "@playwright/test"
import type { CloudAccountCreatePayload } from "../src/types/cloud-assessment"
import { expect, test } from "@playwright/test"
import {
	ACCOUNT,
	ACCOUNT_ID,
	AVAILABILITY,
	CHECKS,
	CUSTOMER,
	FINDINGS,
	FRAMEWORK,
	HOSTILE_DETAIL,
	LATEST,
	REQUIREMENTS,
	SCANS
} from "./cloud-assessment-fixtures"
import { openCustomerSection } from "./customer-sections"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * Cloud Security Assessment (#1328) in a real browser: the page's URL state (an account opened
 * from the list, browser Back), the failures over time drawn by ECharts (a column opens its scan),
 * the scan's tabs, what the customer's cloud reported shown as text,
 * Prowler's Markdown rendered without links it shouldn't have, the report as a download, and the
 * customer's Cloud Accounts section adding an AWS role. Tenancy and the API are the backend's tests.
 */

interface Mock {
	findingRequests: URL[]
	creates: CloudAccountCreatePayload[]
}

async function installCloudMock(context: BrowserContext): Promise<Mock> {
	const mock: Mock = { findingRequests: [], creates: [] }
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })
	const base = `/cloud_assessment/${CUSTOMER}`
	const scanRoute = new RegExp(`^${base}/scans/(\\d+)(/.+)$`)

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")
			const method = route.request().method()
			const list = { encryption_key_configured: true, runner_configured: true }
			// A scan's own routes, for any of the account's scans (the chart opens older ones).
			const scanMatch = scanRoute.exec(path)
			const scanPath = scanMatch && SCANS.some(scan => String(scan.id) === scanMatch[1]) ? scanMatch[2] : null

			if (path === "/cloud_assessment/availability") return json(route, { success: true, ...AVAILABILITY })
			if (path === "/cloud_assessment/accounts") return json(route, { success: true, accounts: [ACCOUNT], ...list })
			if (path === `${base}/accounts` && method === "GET") return json(route, { success: true, accounts: [ACCOUNT], ...list })
			if (path === `${base}/accounts` && method === "POST") {
				const body = route.request().postDataJSON() as CloudAccountCreatePayload
				mock.creates.push(body)
				return json(route, {
					success: true,
					account: { ...ACCOUNT, id: 7, name: body.name, secret_configured: false, secret_hint: null, last_scan: null, last_completed_scan: null }
				})
			}
			if (path === `${base}/accounts/${ACCOUNT_ID}`) return json(route, { success: true, account: ACCOUNT })
			if (path === `${base}/scans`) return json(route, { success: true, scans: SCANS, total: SCANS.length, page: 1, page_size: 100 })
			if (scanPath === "/checks") {
				return json(route, { success: true, checks: CHECKS, services: ["ec2"], total: CHECKS.length, page: 1, page_size: 50 })
			}
			if (scanPath === "/findings") {
				mock.findingRequests.push(url)
				return json(route, { success: true, findings: FINDINGS, total: FINDINGS.length, page: 1, page_size: 50 })
			}
			if (scanPath === "/compliance") return json(route, { success: true, frameworks: [FRAMEWORK], catalog_available: true })
			if (scanPath === `/compliance/${FRAMEWORK.key}`) {
				return json(route, { success: true, framework: FRAMEWORK, requirements: REQUIREMENTS, catalog_available: true })
			}
			if (scanPath === "/reports/html") {
				return route.fulfill({ status: 200, contentType: "application/octet-stream", body: "<html><body>Prowler</body></html>" })
			}
			if (path === `/customers/${CUSTOMER}/full`) {
				return json(route, {
					success: true,
					customer: { customer_code: CUSTOMER, customer_name: "Acme Corp", contact_first_name: "A", contact_last_name: "B" }
				})
			}
			return route.fallback()
		}
	)
	return mock
}

const accountUrl = `/cloud-security-assessment?customer=${CUSTOMER}&account=${ACCOUNT_ID}`

test.describe("Cloud Security Assessment", () => {
	let mock: Mock

	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		mock = await installCloudMock(context)
		await signIn(page)
	})

	test("an account opens from the list on its newest scan, and Back returns to the list", async ({ page }) => {
		await page.goto("/cloud-security-assessment")
		const row = page.getByTestId(`cloud-overview-row-${ACCOUNT_ID}`)
		await expect(row).toContainText("Production")
		await expect(row).toContainText("Acme Corp")
		await expect(page.getByTestId("cloud-runner-version")).toContainText("Prowler 5.52.0")

		await row.click()
		await expect(page).toHaveURL(/customer=ACME&account=1/)
		await expect(page.getByTestId("cloud-scan-view")).toContainText(`Scan #${LATEST}`)
		await expect(page.getByTestId("cloud-scan-tile-new")).toContainText("since #10")
		await expect(page.getByTestId("cloud-scan-row-9")).toContainText("first scan")

		await page.goBack()
		await expect(page.getByTestId("cloud-accounts-overview")).toBeVisible()
	})

	test("failures over time: a column opens its scan, and the table says the same", async ({ page }) => {
		await page.goto(accountUrl)
		const trend = page.getByTestId("cloud-trend")
		await expect(trend).toContainText("3 completed scans")
		const canvas = trend.locator("canvas").first()
		await expect(canvas).toBeVisible()
		const box = await canvas.boundingBox()
		if (!box) throw new Error("the chart has no box")
		// Three columns, oldest on the left: the left fifth is scan 9's slot, above its column too.
		const oldest = { x: box.x + box.width * 0.2, y: box.y + box.height * 0.3 }
		await page.mouse.move(oldest.x, oldest.y)
		await expect(page.getByText(/Scan #9 ·/)).toBeVisible()
		await page.mouse.click(oldest.x, oldest.y)
		await expect(page).toHaveURL(/scan=9/)
		await expect(page.getByTestId("cloud-scan-view")).toContainText("Scan #9")

		await trend.getByTestId("cloud-trend-view-table").click()
		await expect(trend.getByTestId(`cloud-trend-row-${LATEST}`)).toContainText("5 new, 2 resolved")
		await expect(trend.getByTestId("cloud-trend-row-9")).toContainText("first scan")
	})

	test("a finding's detail from the customer's cloud is text, never markup", async ({ page }) => {
		await page.goto(`${accountUrl}&tab=findings`)
		const finding = page.getByTestId(`cloud-finding-${FINDINGS[0]?.id}`)
		await finding.getByRole("button").click()
		const detail = page.getByTestId("cloud-finding-detail")
		await expect(detail).toContainText(HOSTILE_DETAIL)
		await expect(detail.locator("img")).toHaveCount(0)
		expect(await page.evaluate(() => (window as unknown as { __cloudXss?: number }).__cloudXss)).toBeUndefined()
		expect(new URL(mock.findingRequests.at(-1) ?? "http://x").searchParams.get("muted")).toBe("false")
	})

	test("a check shows Prowler's Markdown, links only http(s) references, and leads to its findings", async ({ page }) => {
		await page.goto(`${accountUrl}&tab=checks`)
		const check = page.getByTestId(`cloud-check-${CHECKS[0]?.check_id}`)
		await check.getByRole("button").first().click()
		const detail = page.getByTestId("cloud-check-detail")
		await expect(detail.locator("strong", { hasText: "EC2 instances" })).toBeVisible()
		await expect(detail.locator("a")).toHaveCount(1)
		await expect(detail.locator("a")).toHaveAttribute("href", /^https:\/\/docs\.aws\.amazon\.com\//)
		await expect(detail.locator("a")).toHaveAttribute("rel", "noopener noreferrer")

		await detail.getByRole("button", { name: "Its findings" }).click()
		await expect(page).toHaveURL(/tab=findings&check=ec2_instance_port_ssh_exposed_to_internet/)
		await expect(page.getByTestId("cloud-findings-check")).toContainText(CHECKS[0]?.check_id ?? "")
		await expect
			.poll(() => mock.findingRequests.at(-1)?.searchParams.get("check_id"))
			.toBe("ec2_instance_port_ssh_exposed_to_internet")
	})

	test("a framework's requirements read in order: 1.2 before 1.10", async ({ page }) => {
		await page.goto(`${accountUrl}&tab=compliance`)
		await page.getByTestId(`cloud-framework-${FRAMEWORK.key}`).click()
		await expect(page).toHaveURL(/framework=CIS-5\.0/)
		const ids = page.locator("[data-testid^=cloud-requirement-]")
		await expect(ids).toHaveCount(3)
		expect(await ids.evaluateAll(rows => rows.map(row => row.getAttribute("data-testid")))).toEqual([
			"cloud-requirement-1.1",
			"cloud-requirement-1.2",
			"cloud-requirement-1.10"
		])
	})

	test("Prowler's HTML report downloads as a file", async ({ page }) => {
		await page.goto(accountUrl)
		const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("cloud-report-html").click()])
		expect(download.suggestedFilename()).toBe(`prowler-scan-${LATEST}.html`)
	})

	test("an admin adds an AWS role account and is shown how to create the role", async ({ page }) => {
		await page.goto(`/customers/${CUSTOMER}`)
		await openCustomerSection(page, "Cloud Accounts")
		await page.getByRole("button", { name: "Add account" }).first().click()

		const form = page.getByTestId("cloud-account-form")
		await form.getByTestId("cloud-account-name").locator("input").fill("Staging")
		await form.getByTestId("cloud-account-role-arn").locator("input").fill("arn:aws:iam::123456789012:role/ProwlerScan")
		await form.getByText("CoPilot's own AWS identity").click()
		await form.getByTestId("cloud-account-save").click()

		await expect.poll(() => mock.creates.length).toBe(1)
		expect(mock.creates[0]).toMatchObject({
			name: "Staging",
			provider: "aws",
			auth_method: "role",
			secret: null,
			config: { role_arn: "arn:aws:iam::123456789012:role/ProwlerScan" }
		})
		const setup = page.getByTestId("aws-role-setup")
		await expect(setup.getByTestId("aws-role-external-id")).toHaveText(ACCOUNT.external_id ?? "")
		await expect(setup).toContainText("232136659152")
		await expect(setup.locator("a")).toHaveAttribute("href", /\/blob\/5\.52\.0\/permissions\/templates\/cloudformation\/prowler-scan-role\.yml$/)
	})
})
