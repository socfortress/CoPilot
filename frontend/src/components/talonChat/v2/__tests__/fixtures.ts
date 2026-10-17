import type { TalonAction } from "@/types/talonActions"

export const APPROVAL_ID = "3f1c9a2e-5b7d-4e8f-9a01-2c3d4e5f6a7b"
export const THREAD_ID = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"

/** CoPilot's naive UTC `DATETIME`, `hours` from now. */
export function naiveUtc(hours: number): string {
	return new Date(Date.now() + hours * 3600_000).toISOString().slice(0, 19)
}

/** A proposal as `GET /api/talon/actions/{id}` answers it (`ActionOut`). */
export function talonAction(extra: Partial<TalonAction> = {}): TalonAction {
	return {
		id: APPROVAL_ID,
		thread_id: THREAD_ID,
		customer_code: "ACME",
		requester_user_id: "7",
		requester_username: "ana",
		action: "set_alert_status",
		side_effect: "external-action",
		executes_through: "PUT /api/incidents/db_operations/alert/status",
		target: { alert_id: 840 },
		args: { alert_id: 840, status: "CLOSED" },
		reason: "a known scanner",
		links: false,
		provenance: { untrusted_seen: false, injection_detected: false, web_used: false },
		talon_status: "pending",
		state: "pending",
		state_reason: null,
		expired: false,
		expires_at: naiveUtc(4),
		expires_in_seconds: 4 * 3600,
		result_due_by: null,
		created_at: naiveUtc(0),
		decision: null,
		approver_user_id: null,
		approver_username: null,
		decided_at: null,
		execution_result: null,
		executed_at: null,
		outcome_reported: false,
		can_decide: true,
		is_requester: true,
		...extra
	}
}

/** A quarantine proposal, bound to its host's Velociraptor client. */
export function quarantineAction(extra: Partial<TalonAction> = {}): TalonAction {
	return talonAction({
		action: "quarantine_host",
		side_effect: "endpoint-action",
		executes_through: "POST /api/artifacts/quarantine",
		target: { customer_code: "ACME", agent_id: "001", velociraptor_id: "C.1234567890abcdef", hostname: "WIN-DC01" },
		args: {
			hostname: "WIN-DC01",
			velociraptor_id: "C.1234567890abcdef",
			action: "quarantine",
			artifact_name: "Windows.Remediation.Quarantine"
		},
		...extra
	})
}

export function axiosError(status: number, data: unknown) {
	return Object.assign(new Error("Request failed"), { isAxiosError: true, response: { status, data } })
}

export function response(action: TalonAction, success = true, message = "Action retrieved") {
	return { data: { success, message, action } }
}

/** CoPilot's list answer (`GET /api/talon/actions?scope=…`). */
export function listOf(actions: TalonAction[]) {
	return { data: { success: true, message: `${actions.length} action(s)`, actions } }
}
