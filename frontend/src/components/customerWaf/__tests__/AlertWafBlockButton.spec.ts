import type { CustomerWafInstance } from "@/types/customer-waf"
import { mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ref } from "vue"
import AlertWafBlockButton from "../AlertWafBlockButton.vue"

const instances = ref<CustomerWafInstance[]>([])

vi.mock("../utils", async importOriginal => ({
	...(await importOriginal<typeof import("../utils")>()),
	useCustomerWafs: () => ({ instances })
}))

function waf(over: Partial<CustomerWafInstance> = {}): CustomerWafInstance {
	return {
		id: 1,
		customer_code: "ACME",
		name: "prod",
		api_url: "https://waf:8443",
		token_prefix: "wafst_abc...",
		verify_tls: false,
		has_ca_cert: false,
		enabled: true,
		last_verified_at: "2026-09-23T10:00:00",
		last_verified_role: "admin,operator,viewer",
		created_by: null,
		created_at: null,
		updated_by: null,
		updated_at: null,
		...over
	}
}

function render(value = "203.0.113.7") {
	return mount(AlertWafBlockButton, {
		props: { customerCode: "ACME", value, alertId: 42 },
		global: { stubs: { CustomerWafBlockDialog: true } }
	})
}

describe("alertWafBlockButton", () => {
	beforeEach(() => {
		instances.value = [waf()]
	})

	it("offers blocking an IP IoC when the customer has a block-capable WAF", () => {
		expect(render().text()).toContain("Block at WAF")
	})

	it("renders nothing for a non-IP IoC", () => {
		expect(render("evil.example.com").text()).toBe("")
	})

	it("renders nothing when the customer has no WAF", () => {
		instances.value = []
		expect(render().text()).toBe("")
	})

	it("renders nothing when the only WAF's token is read-only", () => {
		instances.value = [waf({ last_verified_role: "viewer" })]
		expect(render().text()).toBe("")
	})

	it("renders nothing when the WAF was never verified", () => {
		instances.value = [waf({ last_verified_role: null })]
		expect(render().text()).toBe("")
	})

	it("renders nothing when the block-capable WAF is disabled", () => {
		instances.value = [waf({ enabled: false })]
		expect(render().text()).toBe("")
	})

	it("appears if any one of several WAFs can block", () => {
		instances.value = [waf({ id: 1, last_verified_role: "viewer" }), waf({ id: 2 })]
		expect(render().text()).toContain("Block at WAF")
	})
})
