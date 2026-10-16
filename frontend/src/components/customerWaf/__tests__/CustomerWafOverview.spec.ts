import type { CustomerWafInstance, CustomerWafStats } from "@/types/customer-waf"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import CustomerWafOverview from "../CustomerWafOverview.vue"

const getStats = vi.fn()

vi.mock("@/api", () => ({
	default: { customerWaf: { getStats: (...args: unknown[]) => getStats(...args) } }
}))

const instance: CustomerWafInstance = {
	id: 7,
	customer_code: "ACME",
	name: "prod",
	api_url: "https://waf:8443",
	token_prefix: "wafst_abc...",
	verify_tls: false,
	has_ca_cert: false,
	enabled: true,
	last_verified_at: null,
	last_verified_role: "viewer",
	created_by: null,
	created_at: null,
	updated_by: null,
	updated_at: null,
	syslog_host: null,
	syslog_port: null,
	graylog_input_id: null,
	graylog_stream_id: null,
	graylog_index_set_id: null,
	forwarding_provisioned_at: null
}

const stats: CustomerWafStats = {
	total_1h: 1234,
	blocked_1h: 12,
	detected_1h: 3,
	block_rate: 0.01,
	top_rules: [],
	top_ips: [],
	requests_per_hour: [],
	attack_categories: [],
	top_countries: [],
	ingestion_lag_seconds: null,
	events_per_minute: null,
	caddy_healthy: true
} as CustomerWafStats

const timeoutError = {
	isAxiosError: true,
	response: {
		status: 502,
		data: { detail: "WAF 'prod' did not answer within 120s", reason: "timeout", success: false }
	}
}

function deferred<T>() {
	let resolve!: (v: T) => void
	let reject!: (e: unknown) => void
	const promise = new Promise<T>((res, rej) => {
		resolve = res
		reject = rej
	})
	return { promise, resolve, reject }
}

function render() {
	return mount(CustomerWafOverview, {
		props: { customerCode: "ACME", instance },
		global: { stubs: { CustomerWafBlockDialog: true, WafRequestsChart: true, WafRankList: true } }
	})
}

describe("customerWafOverview", () => {
	beforeEach(() => {
		vi.useFakeTimers()
		getStats.mockReset()
	})

	afterEach(() => {
		vi.useRealTimers()
	})

	it("asks for this WAF's stats", async () => {
		getStats.mockResolvedValue({ data: { stats } })
		render()
		await flushPromises()
		expect(getStats).toHaveBeenCalledWith("ACME", 7)
	})

	it("says why it is still loading once the wait is long, and drops the note when stats land", async () => {
		const pending = deferred<{ data: { stats: CustomerWafStats } }>()
		getStats.mockReturnValue(pending.promise)
		const wrapper = render()

		await vi.advanceTimersByTimeAsync(7000)
		expect(wrapper.find("[data-testid=waf-overview-slow]").exists()).toBe(false)

		await vi.advanceTimersByTimeAsync(1500)
		expect(wrapper.find("[data-testid=waf-overview-slow]").text()).toContain("up to two minutes")

		pending.resolve({ data: { stats } })
		await flushPromises()
		expect(wrapper.find("[data-testid=waf-overview-slow]").exists()).toBe(false)
		expect(wrapper.text()).toContain("1,234")
	})

	it("never shows the note when stats arrive quickly", async () => {
		getStats.mockResolvedValue({ data: { stats } })
		const wrapper = render()
		await flushPromises()
		await vi.advanceTimersByTimeAsync(20000)
		expect(wrapper.find("[data-testid=waf-overview-slow]").exists()).toBe(false)
	})

	it("explains a timeout as a slow WAF, not a network problem, and offers to try again", async () => {
		getStats.mockRejectedValue(timeoutError)
		const wrapper = render()
		await flushPromises()

		const error = wrapper.find("[data-testid=waf-overview-error]")
		expect(error.text()).toContain("did not answer within 120s")
		expect(error.text()).toContain("reachable but answered too slowly")
		expect(error.text()).not.toContain("can't reach the WAF")
		expect(error.find("button").text()).toContain("Try again")
	})

	it("loads again on Try again and shows the stats when they come", async () => {
		getStats.mockRejectedValueOnce(timeoutError).mockResolvedValueOnce({ data: { stats } })
		const wrapper = render()
		await flushPromises()

		await wrapper.find("[data-testid=waf-overview-error] button").trigger("click")
		await flushPromises()

		expect(getStats).toHaveBeenCalledTimes(2)
		expect(wrapper.find("[data-testid=waf-overview-error]").exists()).toBe(false)
		expect(wrapper.text()).toContain("1,234")
	})

	it("starts the slow-wait clock afresh on Try again", async () => {
		const retry = deferred<{ data: { stats: CustomerWafStats } }>()
		getStats.mockRejectedValueOnce(timeoutError).mockReturnValueOnce(retry.promise)
		const wrapper = render()
		await flushPromises()

		await wrapper.find("[data-testid=waf-overview-error] button").trigger("click")
		await vi.advanceTimersByTimeAsync(7000)
		expect(wrapper.find("[data-testid=waf-overview-slow]").exists()).toBe(false)
		await vi.advanceTimersByTimeAsync(1500)
		expect(wrapper.find("[data-testid=waf-overview-slow]").exists()).toBe(true)
	})

	it("leaves no timer behind when the page is left mid-wait", async () => {
		getStats.mockReturnValue(new Promise(() => {}))
		const wrapper = render()
		await flushPromises()
		expect(vi.getTimerCount()).toBe(1)
		wrapper.unmount()
		expect(vi.getTimerCount()).toBe(0)
	})
})
