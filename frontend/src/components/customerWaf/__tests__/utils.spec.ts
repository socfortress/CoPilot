import type { CustomerWafInstance } from "@/types/customer-waf"
import { describe, expect, it } from "vitest"
import { capabilitiesFromRoles, flag, looksLikeIp, wafCapabilityLabel } from "../utils"

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
		last_verified_at: null,
		last_verified_role: null,
		created_by: null,
		created_at: null,
		updated_by: null,
		updated_at: null,
		...over
	}
}

describe("capabilitiesFromRoles (mirror of the backend role table)", () => {
	it.each([
		["viewer", true, false, false],
		["admin", true, true, true],
		// operator can write rules but not read sites — can block, can't drive the read views
		["operator", false, true, false],
		["admin,operator,viewer", true, true, true],
		["viewer,operator", true, true, false],
		["", false, false, false],
		["someone-elses-role", false, false, false]
	])("%s", (roles, read, block, forwarders) => {
		expect(capabilitiesFromRoles(roles)).toEqual({
			can_read: read,
			can_block: block,
			can_manage_forwarders: forwarders
		})
	})

	it("accepts an array of roles", () => {
		expect(capabilitiesFromRoles(["viewer", "operator"]).can_block).toBe(true)
	})
})

describe("wafCapabilityLabel", () => {
	it("is 'Not verified' until a connection test has run", () => {
		expect(wafCapabilityLabel(waf()).label).toBe("Not verified")
	})
	it("distinguishes read-only from block-capable", () => {
		expect(wafCapabilityLabel(waf({ last_verified_role: "viewer" })).label).toBe("Read-only")
		expect(wafCapabilityLabel(waf({ last_verified_role: "admin,viewer" })).label).toBe("Can block")
	})
})

describe("looksLikeIp", () => {
	it.each(["203.0.113.7", "203.0.113.0/24", " 8.8.8.8 ", "2001:db8::1", "2001:db8::/48"])("%s is an IP", v => {
		expect(looksLikeIp(v)).toBe(true)
	})
	it.each(["evil.com", "256.1.1.1", "1.2.3", "d41d8cd98f00b204e9800998ecf8427e", "", "http://1.2.3.4/x"])(
		"%s is not",
		v => {
			expect(looksLikeIp(v)).toBe(false)
		}
	)
})

describe("flag", () => {
	it("turns an ISO alpha-2 code into its flag emoji, case-insensitively", () => {
		expect(flag("FR")).toBe("🇫🇷")
		expect(flag("us")).toBe("🇺🇸")
	})
	it.each([null, undefined, "", "XYZ", "1A"])("falls back to a globe for %s", code => {
		expect(flag(code)).toBe("🌐")
	})
})
