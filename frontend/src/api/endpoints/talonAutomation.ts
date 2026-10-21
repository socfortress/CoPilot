import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

/**
 * Talon v2 automation policy (talon-analyst D85, plan AUTOMATION-POLICY.md AP-2): what an automatic
 * investigation may run on the alert's own host, per customer, and the global switch. Every shape
 * the UI reads or sends lives in this module, matching CoPilot's
 * `connectors/talon/schema/talon_automation.py`.
 *
 * - `GET`/`PUT /talon/v2/automation/{customer_code}`: the customer's policy. No row means every
 *   level is `off` (`exists: false`, `version: 0`). The `PUT` is a full replacement: the four modes
 *   every time, and `level_2_artifacts`, `file_allow_globs` and `caps` null when unset. A `PUT` that
 *   raises level 3 or 4 must carry `acknowledge_risk: true` (400 otherwise); `expected_version` is
 *   the version read (409 if another admin changed it); raising any level for a customer the Talon
 *   service user isn't assigned is a 409.
 * - `GET`/`PUT /talon/v2/settings/automation`: the global `automation_enabled` kill switch.
 *
 * Both are admin only (token scope and database role), refuse the Talon service account, and answer
 * whatever the "Talon v2" setting says (the policy is set before the start route is turned on).
 * A refusal's text is read by `talonFailure` (`detail` or `message`).
 */

/** A level's mode. `shadow` records what would have run and runs nothing; only `auto` executes. */
export type TalonAutomationMode = "off" | "shadow" | "propose" | "auto"

export const AUTOMATION_MODES: readonly TalonAutomationMode[] = ["off", "shadow", "propose", "auto"]

/** The order the policy compares modes in (CoPilot's `RANK`): `off` < `shadow` < `propose` < `auto`. */
export const MODE_RANK: Record<TalonAutomationMode, number> = { off: 0, shadow: 1, propose: 2, auto: 3 }

export type TalonAutomationLevel = 1 | 2 | 3 | 4

export const AUTOMATION_LEVELS: readonly TalonAutomationLevel[] = [1, 2, 3, 4]

/** Levels whose raise needs the admin's acknowledgement of the honest risk (Q7). */
export const RISK_LEVELS: readonly TalonAutomationLevel[] = [3, 4]

export type TalonAutomationModes = Record<`level_${TalonAutomationLevel}_mode`, TalonAutomationMode>

export type TalonAutomationFileOs = "windows" | "linux"

/** `GET`/`PUT /talon/v2/automation/{customer_code}`'s answer (`TalonAutomationPolicyResponse`). */
export interface TalonAutomationPolicy extends FlaskBaseResponse, TalonAutomationModes {
	customer_code: string
	/** False while the customer has no row (every level `off`). */
	exists: boolean
	/** The global switch, as now. */
	automation_enabled: boolean
	/** Level 2's catalogue artifacts, stored for later. Not edited here; sent back unchanged. */
	level_2_artifacts: string[] | null
	/** Level 2's file allow globs per OS, stored for later. Not edited here; sent back unchanged. */
	file_allow_globs: Partial<Record<TalonAutomationFileOs, string[]>> | null
	/** The overrides as stored, by cap name. */
	caps: Record<string, number> | null
	/** Every cap with the overrides applied. */
	effective_caps: Record<string, number>
	cap_defaults: Record<string, number>
	/** The caps CoPilot enforces on starts today; the others are stored for the levels that use them. */
	enforced_caps: string[]
	/** The levels CoPilot can start in `auto` today; the others' starts are refused, but are settable. */
	startable_levels: number[]
	/** False: the Talon service user isn't assigned this customer, so no level can be raised. */
	service_user_assigned: boolean
	/** The honest-risk text the admin acknowledges to raise level 3 or 4. */
	risk_acknowledgement_text: string
	risk_acknowledged_by_user_id: number | null
	risk_acknowledged_by_username: string | null
	risk_acknowledged_at: string | null
	shadow_reviewed: Record<string, Record<string, unknown>> | null
	/** 0 when there is no row. */
	version: number
	updated_by_user_id: number | null
	updated_by_username: string | null
	updated_at: string | null
}

/** `PUT /talon/v2/automation/{customer_code}`'s body (`TalonAutomationPolicyUpdate`, strict). */
export interface TalonAutomationPolicyUpdate extends TalonAutomationModes {
	level_2_artifacts: string[] | null
	file_allow_globs: Partial<Record<TalonAutomationFileOs, string[]>> | null
	/** Cap overrides by name, each between 0 and its default; null: none. */
	caps: Record<string, number> | null
	acknowledge_risk: boolean
	expected_version: number
}

/** `GET`/`PUT /talon/v2/settings/automation`'s answer (`TalonAutomationSwitchResponse`). */
export interface TalonAutomationSettings extends FlaskBaseResponse {
	connector_name: string
	automation_enabled: boolean
	updated_by_user_id: number | null
	updated_at: string | null
}

export function modesOf(policy: TalonAutomationModes): TalonAutomationModes {
	return {
		level_1_mode: policy.level_1_mode,
		level_2_mode: policy.level_2_mode,
		level_3_mode: policy.level_3_mode,
		level_4_mode: policy.level_4_mode
	}
}

export function modeKey(level: TalonAutomationLevel): `level_${TalonAutomationLevel}_mode` {
	return `level_${level}_mode`
}

/** The levels this change raises (to a higher mode than they had), as CoPilot computes them. */
export function raisedLevels(before: TalonAutomationModes, after: TalonAutomationModes): TalonAutomationLevel[] {
	return AUTOMATION_LEVELS.filter(level => MODE_RANK[after[modeKey(level)]] > MODE_RANK[before[modeKey(level)]])
}

/** The levels 3–4 this change raises: each needs the acknowledgement. */
export function riskRaises(before: TalonAutomationModes, after: TalonAutomationModes): TalonAutomationLevel[] {
	return raisedLevels(before, after).filter(level => RISK_LEVELS.includes(level))
}

/**
 * The full-replacement body: the edited modes and cap overrides (an empty override is the default,
 * and no override at all is null), level 2's lists as read, and the version read.
 */
export function buildPolicyUpdate(
	policy: TalonAutomationPolicy,
	modes: TalonAutomationModes,
	capOverrides: Record<string, number | null | undefined>,
	acknowledgeRisk: boolean
): TalonAutomationPolicyUpdate {
	const caps: Record<string, number> = {}
	for (const [name, value] of Object.entries(capOverrides)) {
		if (name in policy.cap_defaults && typeof value === "number") caps[name] = value
	}
	return {
		...modesOf(modes),
		level_2_artifacts: policy.level_2_artifacts ? [...policy.level_2_artifacts] : null,
		file_allow_globs: policy.file_allow_globs ? { ...policy.file_allow_globs } : null,
		caps: Object.keys(caps).length ? caps : null,
		acknowledge_risk: acknowledgeRisk,
		expected_version: policy.version
	}
}

export default {
	getPolicy(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<TalonAutomationPolicy>(`/talon/v2/automation/${encodeURIComponent(customerCode)}`, {
			signal
		})
	},
	putPolicy(customerCode: string, body: TalonAutomationPolicyUpdate) {
		return HttpClient.put<TalonAutomationPolicy>(`/talon/v2/automation/${encodeURIComponent(customerCode)}`, body)
	},
	getSettings(signal?: AbortSignal) {
		return HttpClient.get<TalonAutomationSettings>(`/talon/v2/settings/automation`, { signal })
	},
	putSettings(automationEnabled: boolean) {
		return HttpClient.put<TalonAutomationSettings>(`/talon/v2/settings/automation`, {
			automation_enabled: automationEnabled
		})
	}
}
