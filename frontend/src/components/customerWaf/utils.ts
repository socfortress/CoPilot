import type { CustomerWafCapabilities, CustomerWafFailureReason, CustomerWafInstance } from "@/types/customer-waf"
import { ref } from "vue"
import Api from "@/api"

// Mirror of backend app/customer_waf/services/customer_waf.py:WAF_ROLE_PERMISSIONS, used only to
// describe a WAF from its cached role (`last_verified_role`) without calling it. The WAF enforces
// its own role table on every request; this never authorises anything.
const ROLE_PERMISSIONS: Record<string, string[]> = {
	admin: ["sites:read", "rules:read", "rules:write", "config:read", "config:write", "logs:read"],
	operator: ["rules:read", "rules:write", "logs:read"],
	viewer: ["sites:read", "rules:read", "config:read", "logs:read"]
}

export function capabilitiesFromRoles(roles: string | string[] | null | undefined): CustomerWafCapabilities {
	const list = Array.isArray(roles) ? roles : (roles || "").split(",").map(r => r.trim())
	const perms = new Set(list.flatMap(r => ROLE_PERMISSIONS[r] ?? []))
	return {
		can_read: perms.has("sites:read") && perms.has("logs:read"),
		can_block: perms.has("rules:read") && perms.has("rules:write"),
		can_manage_forwarders: perms.has("config:write")
	}
}

export function wafCapabilityLabel(instance: CustomerWafInstance): { label: string; type: "success" | "info" | "default" } {
	if (!instance.last_verified_role) return { label: "Not verified", type: "default" }
	const caps = capabilitiesFromRoles(instance.last_verified_role)
	if (caps.can_block) return { label: "Can block", type: "success" }
	if (caps.can_read) return { label: "Read-only", type: "info" }
	return { label: "No access", type: "default" }
}

const IPV4 = /^(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?:\/(?:3[0-2]|[12]?\d))?$/
const IPV6 = /^[0-9a-f:]+(?:\/\d{1,3})?$/i

/** Cheap client-side check for showing "Block at WAF". The backend does the real validation. */
export function looksLikeIp(value: string | null | undefined): boolean {
	const v = (value || "").trim()
	return IPV4.test(v) || (v.includes(":") && IPV6.test(v))
}

/** A one-line explanation for a WAF failure `reason`, shown next to the backend's detail. */
export function reasonHint(reason: CustomerWafFailureReason | string | null | undefined): string | null {
	switch (reason) {
		case "unreachable":
			return "CoPilot can't reach the WAF. Check the URL, and that the WAF admin port is reachable from CoPilot."
		case "tls_error":
			return "TLS verification failed. Turn verification off for a self-signed WAF, or add its CA certificate."
		case "token_rejected":
			return "The WAF rejected the token. Issue a new one in the WAF under Service Tokens and update it here."
		case "insufficient_role":
			return "The token's WAF user lacks the needed role. Blocking needs admin or operator."
		case "not_a_waf":
			return "Something answered at that URL, but not a SOCFortress WAF API."
		case "token_crypto":
			return "The stored token can't be decrypted (WAF_TOKEN_ENCRYPTION_KEY changed or is missing). Re-enter the token."
		case "disabled":
			return "This WAF is disabled in CoPilot."
		default:
			return null
	}
}

// Per-customer cache so an alert with many IP IoCs asks for the customer's WAFs once, not once per IoC.
const instancesCache = new Map<string, Promise<CustomerWafInstance[]>>()

export function invalidateCustomerWafs(customerCode: string) {
	instancesCache.delete(customerCode)
}

export function useCustomerWafs(customerCode: string) {
	const instances = ref<CustomerWafInstance[]>([])
	if (!instancesCache.has(customerCode)) {
		instancesCache.set(
			customerCode,
			Api.customerWaf
				.getInstances(customerCode)
				.then(res => (res.data.success ? res.data.instances : []))
				.catch(() => {
					instancesCache.delete(customerCode)
					return []
				})
		)
	}
	instancesCache.get(customerCode)?.then(list => {
		instances.value = list
	})
	return { instances }
}

/** ISO 3166 alpha-2 → flag emoji (regional-indicator pair); a globe when unknown. */
export function flag(code: string | null | undefined): string {
	if (!code || !/^[A-Z]{2}$/i.test(code)) return "🌐"
	return String.fromCodePoint(...[...code.toUpperCase()].map(ch => 0x1F1E6 + ch.charCodeAt(0) - 65))
}
