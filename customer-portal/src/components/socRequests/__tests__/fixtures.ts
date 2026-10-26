import type { SocRequest } from "@/types/socRequests"

export function request(id: number, extra: Partial<SocRequest> = {}): SocRequest {
	return {
		id,
		case_id: null,
		alert_id: null,
		origin_alert_id: null,
		question: "Is this sign-in our VPN?",
		urgency: "normal",
		status: "open",
		requested_by: "jane",
		requested_at: "2026-10-24T07:00:00Z",
		answered_at: null,
		...extra
	}
}
