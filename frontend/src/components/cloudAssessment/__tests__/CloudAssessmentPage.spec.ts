/**
 * The Cloud Security Assessment page (#1328): the cross-customer overview, an account and its
 * scans, and a scan's tabs, all driven by the URL. Untrusted text from the customer's cloud is
 * shown as text, and only http(s) references become links.
 */
import type { VueWrapper } from "@vue/test-utils"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { routes } from "@/router/routes"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import CloudAssessmentPage from "../CloudAssessmentPage.vue"
import { resetCloudAvailability } from "../useCloudAvailability"
import { account, check, counts, finding, framework, requirement, scan, SCAN_COUNTS } from "./fixtures"

const api = vi.hoisted(() => ({
	availability: vi.fn(),
	getAllAccounts: vi.fn(),
	getAccount: vi.fn(),
	getScans: vi.fn(),
	getChecks: vi.fn(),
	getFindings: vi.fn(),
	getCompliance: vi.fn(),
	getComplianceFramework: vi.fn(),
	testConnection: vi.fn(),
	startScan: vi.fn(),
	cancelScan: vi.fn(),
	deleteScan: vi.fn(),
	downloadReport: vi.fn()
}))
const customers = vi.hoisted(() => ({ getCustomers: vi.fn() }))
const saveAs = vi.hoisted(() => vi.fn())

vi.mock("@/api", () => ({ default: { cloudAssessment: api, customers } }))
vi.mock("file-saver", () => ({ saveAs }))

const globalCodes = ref<string[]>([])
vi.mock("@/composables/useGlobalCustomerFilter", () => ({
	useGlobalCustomerFilter: () => ({ globalCustomerCodes: globalCodes, onGlobalCustomerFilterChange: vi.fn() })
}))

const LAST = {
	id: 11,
	status: "completed" as const,
	trigger_type: "manual" as const,
	queued_at: null,
	completed_at: "2026-11-20T10:20:00",
	counts: SCAN_COUNTS,
	error_code: null,
	previous_scan_id: 10
}
const ACME = account({ last_scan: LAST, last_completed_scan: LAST })
const GLOBEX = account({
	id: 2,
	customer_code: "GLOBEX",
	name: "Globex tenant",
	provider: "azure",
	auth_method: "client_secret",
	cloud_account: "11111111-2222-3333-4444-555555555555"
})

let wrapper: VueWrapper | null = null

function current(): VueWrapper {
	if (!wrapper) throw new Error("render() first")
	return wrapper
}

async function render(path = "/cloud-security-assessment") {
	const router = createRouter({ history: createMemoryHistory(), routes })
	await router.push(path)
	await router.isReady()
	wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(CloudAssessmentPage)) }), {
		global: { plugins: [router] },
		attachTo: document.body
	})
	await flushPromises()
	return router
}

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "analyst1", email: "", role }
}

const button = (text: string) => current().findAll("button").find(b => b.text().trim() === text)

beforeEach(() => {
	setActivePinia(createPinia())
	signInAs(AuthUserRole.Admin)
	resetCloudAvailability()
	globalCodes.value = []
	for (const fn of Object.values(api)) fn.mockReset()
	customers.getCustomers.mockReset()
	api.availability.mockResolvedValue({
		data: {
			encryption_key_configured: true,
			runner_configured: true,
			runner_reachable: true,
			runner_problem: null,
			runner_version: "1.0.0",
			prowler_version: "5.13.1",
			powershell: true,
			providers: ["aws", "azure", "gcp", "m365"]
		}
	})
	api.getAllAccounts.mockResolvedValue({ data: { accounts: [ACME, GLOBEX], encryption_key_configured: true, runner_configured: true } })
	customers.getCustomers.mockResolvedValue({
		data: {
			customers: [
				{ customer_code: "ACME", customer_name: "Acme Corp" },
				{ customer_code: "GLOBEX", customer_name: "Globex" }
			]
		}
	})
	api.getAccount.mockResolvedValue({ data: { account: ACME } })
	api.getScans.mockResolvedValue({
		data: {
			scans: [scan(12, { status: "running", completed_at: null, counts: counts() }), scan(11), scan(10, { previous_scan_id: null })],
			total: 3,
			page: 1,
			page_size: 100
		}
	})
	api.getChecks.mockResolvedValue({ data: { checks: [check("s3_bucket_public_access")], services: ["s3"], total: 1, page: 1, page_size: 50 } })
	api.getFindings.mockResolvedValue({ data: { findings: [finding(1)], total: 1, page: 1, page_size: 50 } })
	api.getCompliance.mockResolvedValue({ data: { frameworks: [framework("CIS-2.0")], catalog_available: true } })
})

afterEach(() => {
	wrapper?.unmount()
	wrapper = null
	document.body.innerHTML = ""
})

describe("the overview", () => {
	it("lists every customer's accounts by customer name, with the headline figures", async () => {
		await render()
		const row = current().find("[data-testid=cloud-overview-row-1]")
		expect(row.text()).toContain("Production")
		expect(row.text()).toContain("Acme Corp")
		expect(row.text()).toContain("+5 new")
		expect(current().find("[data-testid=cloud-overview-row-2]").text()).toContain("Never scanned")
		expect(current().find("[data-testid=cloud-tile-accounts]").text()).toContain("2")
		expect(current().find("[data-testid=cloud-tile-critical]").text()).toContain("3 / 20")
		expect(current().find("[data-testid=cloud-runner-version]").text()).toContain("Prowler 5.13.1")
	})

	it("says an account's only scan is its first, never \"+0 new\"", async () => {
		const first = { ...LAST, previous_scan_id: null }
		api.getAllAccounts.mockResolvedValue({
			data: { accounts: [account({ last_scan: first, last_completed_scan: first })], encryption_key_configured: true, runner_configured: true }
		})
		await render()
		const row = current().find("[data-testid=cloud-overview-row-1]")
		expect(row.text()).toContain("First scan")
		expect(row.text()).not.toContain("new")
	})

	it("starts on the sidebar's customers", async () => {
		globalCodes.value = ["GLOBEX"]
		await render()
		expect(current().find("[data-testid=cloud-overview-row-1]").exists()).toBe(false)
		expect(current().find("[data-testid=cloud-overview-row-2]").exists()).toBe(true)
	})

	it("says where to add an account when there is none", async () => {
		api.getAllAccounts.mockResolvedValue({ data: { accounts: [], encryption_key_configured: true, runner_configured: true } })
		await render()
		expect(current().find("[data-testid=cloud-overview-empty]").text()).toContain("Cloud Accounts")
	})

	it("warns when copilot-prowler can't be reached", async () => {
		api.availability.mockResolvedValue({
			data: { runner_configured: true, runner_reachable: false, runner_problem: "copilot-prowler didn't answer.", prowler_version: null }
		})
		await render()
		expect(current().find("[data-testid=cloud-runner-problem]").text()).toContain("copilot-prowler didn't answer.")
	})

	it("opens an account in the URL, and Back to the list drops the account's keys", async () => {
		const router = await render()
		await current().find("[data-testid=cloud-overview-row-1]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({ customer: "ACME", account: "1" })
		expect(current().find("[data-testid=cloud-account-detail]").exists()).toBe(true)
		expect(api.getAccount).toHaveBeenCalledWith("ACME", 1)

		await router.replace({ query: { ...router.currentRoute.value.query, scan: "10", tab: "checks" } })
		await flushPromises()
		await button("All cloud accounts")?.trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({})
		expect(current().find("[data-testid=cloud-accounts-overview]").exists()).toBe(true)
	})
})

describe("an account", () => {
	it("opens on its newest completed scan; the URL picks another", async () => {
		const router = await render("/cloud-security-assessment?customer=ACME&account=1")
		expect(current().find("[data-testid=cloud-scan-view]").text()).toContain("Scan #11")
		expect(api.getChecks).toHaveBeenCalledWith("ACME", 11, { status: "fail", page_size: 8 })

		await current().find("[data-testid=cloud-scan-row-10]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.scan).toBe("10")
		expect(current().find("[data-testid=cloud-scan-view]").text()).toContain("Scan #10")
	})

	it("compares a scan with the one before, and a first scan with nothing", async () => {
		const router = await render("/cloud-security-assessment?customer=ACME&account=1")
		expect(current().find("[data-testid=cloud-scan-tile-new]").text()).toContain("5")
		expect(current().find("[data-testid=cloud-scan-tile-new]").text()).toContain("since #10")
		expect(current().find("[data-testid=cloud-scan-row-11]").text()).toContain("5 new, 2 resolved")
		expect(current().find("[data-testid=cloud-scan-row-10]").text()).toContain("first scan")

		await router.replace({ query: { ...router.currentRoute.value.query, scan: "10", tab: "findings" } })
		await flushPromises()
		expect(current().find("[data-testid=cloud-findings]").text()).not.toContain("New since the scan before")
		await router.replace({ query: { ...router.currentRoute.value.query, tab: "overview" } })
		await flushPromises()
		const tile = current().find("[data-testid=cloud-scan-tile-new]").text()
		expect(tile).toContain("—")
		expect(tile).toContain("first scan")
	})

	it("says why a scan failed", async () => {
		api.getScans.mockResolvedValue({
			data: {
				scans: [
					scan(13, {
						status: "failed",
						error_code: "auth_failed",
						error_message: "The cloud refused the credentials.",
						prowler_errors: ["ClientAuthenticationError"]
					})
				],
				total: 1,
				page: 1,
				page_size: 100
			}
		})
		await render("/cloud-security-assessment?customer=ACME&account=1")
		const alert = current().find("[data-testid=cloud-scan-error]")
		expect(alert.text()).toContain("The cloud refused the credentials.")
		expect(alert.text()).toContain("ClientAuthenticationError")
	})

	it("reads a scan's worst checks once the scan it shows completes", async () => {
		api.getScans.mockResolvedValue({
			data: { scans: [scan(14, { status: "running", counts: counts(), completed_at: null })], total: 1, page: 1, page_size: 100 }
		})
		vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] })
		try {
			await render("/cloud-security-assessment?customer=ACME&account=1&scan=14")
			expect(api.getChecks).not.toHaveBeenCalled()

			api.getScans.mockResolvedValue({ data: { scans: [scan(14)], total: 1, page: 1, page_size: 100 } })
			vi.advanceTimersByTime(10_000)
			await flushPromises()
			expect(api.getChecks).toHaveBeenCalledWith("ACME", 14, { status: "fail", page_size: 8 })
		} finally {
			vi.useRealTimers()
		}
	})

	it("offers no Cancel once the results are being stored", async () => {
		api.getScans.mockResolvedValue({
			data: { scans: [scan(14, { status: "ingesting", counts: counts() })], total: 1, page: 1, page_size: 100 }
		})
		await render("/cloud-security-assessment?customer=ACME&account=1&scan=14")
		expect(current().find("[data-testid=cloud-scan-active]").text()).toContain("storing the results")
		expect(button("Cancel scan")).toBeUndefined()
	})

	it("lets an admin delete a finished scan, never an analyst", async () => {
		await render("/cloud-security-assessment?customer=ACME&account=1")
		expect(button("Delete scan")).toBeDefined()
		current().unmount()

		signInAs(AuthUserRole.Analyst)
		await render("/cloud-security-assessment?customer=ACME&account=1")
		expect(button("Delete scan")).toBeUndefined()
		expect(button("Settings")).toBeDefined()
	})

	it("downloads a report as a file", async () => {
		const blob = new Blob(["<html></html>"])
		api.downloadReport.mockResolvedValue({ data: blob })
		await render("/cloud-security-assessment?customer=ACME&account=1")
		await current().find("[data-testid=cloud-report-html]").trigger("click")
		await flushPromises()
		expect(api.downloadReport).toHaveBeenCalledWith("ACME", 11, "html")
		expect(saveAs).toHaveBeenCalledWith(blob, "prowler-scan-11.html")
	})
})

describe("a scan's tabs", () => {
	it("filter the findings by the check the URL names, and clearing the check widens them again", async () => {
		const router = await render("/cloud-security-assessment?customer=ACME&account=1&tab=findings&check=s3_bucket_public_access")
		expect(api.getFindings).toHaveBeenLastCalledWith(
			"ACME",
			11,
			expect.objectContaining({ check_id: "s3_bucket_public_access", muted: false, page: 1 }),
			expect.anything()
		)
		const chip = current().find("[data-testid=cloud-findings-check]")
		expect(chip.text()).toContain("s3_bucket_public_access")
		await chip.find(".n-tag__close").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.check).toBeUndefined()
		expect(api.getFindings).toHaveBeenLastCalledWith("ACME", 11, expect.not.objectContaining({ check_id: expect.anything() }), expect.anything())
	})

	it("show what the cloud reported as text, never as markup", async () => {
		api.getFindings.mockResolvedValue({
			data: {
				findings: [finding(7, { status_extended: '<img src=x onerror="alert(1)">', resource_name: "<b>bucket</b>" })],
				total: 1,
				page: 1,
				page_size: 50
			}
		})
		await render("/cloud-security-assessment?customer=ACME&account=1&tab=findings")
		const row = current().find("[data-testid=cloud-finding-7]")
		await row.find("button").trigger("click")
		await flushPromises()
		const detail = current().find("[data-testid=cloud-finding-detail]")
		expect(detail.find("img").exists()).toBe(false)
		expect(row.find("b").exists()).toBe(false)
		expect(detail.text()).toContain('<img src=x onerror="alert(1)">')
		expect(row.text()).toContain("<b>bucket</b>")
	})

	it("link a check's references only when they are http(s), and lead to its findings", async () => {
		api.getChecks.mockResolvedValue({
			data: {
				checks: [
					check("s3_bucket_public_access", {
						description: "<script>alert(1)</script>",
						remediation_urls: ["javascript:alert(1)", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html"],
						additional_urls: ["data:text/html,<b>x</b>"],
						compliance: { "CIS-2.0": ["2.1.4"] }
					})
				],
				services: ["s3"],
				total: 1,
				page: 1,
				page_size: 50
			}
		})
		const router = await render("/cloud-security-assessment?customer=ACME&account=1&tab=checks")
		expect(api.getChecks).toHaveBeenLastCalledWith("ACME", 11, expect.objectContaining({ status: "fail", page: 1 }), expect.anything())
		await current().find("[data-testid=cloud-check-s3_bucket_public_access] button").trigger("click")
		await flushPromises()
		const detail = current().find("[data-testid=cloud-check-detail]")
		const links = detail.findAll("a")
		expect(links.map(a => a.attributes("href"))).toEqual([
			"https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html"
		])
		expect(links[0]?.attributes("rel")).toBe("noopener noreferrer")
		expect(detail.find("script").exists()).toBe(false)
		expect(detail.text()).toContain("CIS-2.0 · 1")

		await detail.findAll("button").find(b => b.text() === "Its findings")?.trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query).toMatchObject({ tab: "findings", check: "s3_bucket_public_access" })
	})

	it("open a framework's requirements, and say which checks didn't run", async () => {
		api.getComplianceFramework.mockResolvedValue({
			data: {
				framework: framework("CIS-2.0", { name: "CIS Amazon Web Services Foundations Benchmark" }),
				requirements: [
					requirement("2.1.4", {
						status: "fail",
						checks: [
							{ check_id: "s3_bucket_public_access", title: null, severity: "critical", passed: 0, failed: 3, manual: 0, muted: 0, ran: true },
							{ check_id: "s3_account_level_public_access_blocks", title: null, severity: "high", passed: 0, failed: 0, manual: 0, muted: 0, ran: false }
						]
					}),
					requirement("1.1", { status: "manual", checks: [] })
				],
				catalog_available: true
			}
		})
		const router = await render("/cloud-security-assessment?customer=ACME&account=1&tab=compliance")
		const row = current().find("[data-testid=cloud-framework-CIS-2\\.0]")
		expect(row.text()).toContain("6 passing")
		expect(row.text()).toContain("2 failing")
		await row.trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.framework).toBe("CIS-2.0")
		expect(api.getComplianceFramework).toHaveBeenCalledWith("ACME", 11, "CIS-2.0")
		const failing = current().find("[data-testid=cloud-requirement-2\\.1\\.4]")
		expect(failing.text()).toContain("Failing")
		expect(failing.text()).toContain("not run")
		expect(current().find("[data-testid=cloud-requirement-1\\.1]").text()).toContain("review it by hand")
	})

	it("say when Prowler's framework catalog couldn't be read", async () => {
		api.getCompliance.mockResolvedValue({ data: { frameworks: [framework("CIS-2.0", { name: null })], catalog_available: false } })
		await render("/cloud-security-assessment?customer=ACME&account=1&tab=compliance")
		expect(current().find("[data-testid=cloud-compliance-no-catalog]").exists()).toBe(true)
		expect(current().find("[data-testid=cloud-framework-CIS-2\\.0]").text()).toContain("CIS-2.0")
	})
})
