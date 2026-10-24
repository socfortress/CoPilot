import type { SocRequest } from "@/types/soc-requests"

export function question(id: number, extra: Partial<SocRequest> = {}): SocRequest {
	return {
		id,
		customer_code: "ACME",
		case_id: null,
		alert_id: null,
		origin_alert_id: null,
		title: null,
		question: "Is this sign-in our VPN?",
		urgency: "normal",
		status: "open",
		requested_by: "jane",
		requested_at: "2026-10-01T12:00:00Z",
		answered_at: null,
		answered_by: null,
		answered_via: null,
		...extra
	}
}
