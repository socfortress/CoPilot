import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

/**
 * Talon v2 automation policy (talon-analyst D85, plan AUTOMATION-POLICY.md AP-2): what an automatic
 * investigation may run on the alert's own host, per customer, and the global switch.
 *
 * Every shape the UI reads or sends lives in this module, so aligning with CoPilot's backend is one
 * edit here. The routes are admin only (token scope and database role) and refuse the Talon service
 * account; a refusal is `{"detail": <fixed text>}` with its status (`talonFailure` reads it).
 *
 * - `GET`/`PUT /talon/v2/automation/{customer_code}`: the customer's row. No row means every level
 *   is `off`. A `PUT` that raises level 3 or 4 must carry `acknowledge_risk: true` (Q7).
 * - `GET`/`PUT /talon/v2/settings/automation`: the global `automation_enabled` kill switch on the
 *   Talon connector's settings row. Off means every automated start is refused, whatever the rows say.
 */

/** A level's mode. `shadow` records what would have run and runs nothing; only `auto` executes. */
export type TalonAutomationMode = "off" | "shadow" | "propose" | "auto"

export const AUTOMATION_MODES: readonly TalonAutomationMode[] = ["off", "shadow", "propose", "auto"]

/** The order the policy uses to compare modes: `off` < `shadow` < `propose` < `auto`. */
export const MODE_RANK: Record<TalonAutomationMode, number> = { off: 0, shadow: 1, propose: 2, auto: 3 }

export type TalonAutomationLevel = 1 | 2 | 3 | 4

export const AUTOMATION_LEVELS: readonly TalonAutomationLevel[] = [1, 2, 3, 4]

/** Levels whose raise needs the admin's acknowledgement of the honest risk (Q7). */
export const RISK_LEVELS: readonly TalonAutomationLevel[] = [3, 4]

export type TalonAutomationModes = Record<`level_${TalonAutomationLevel}_mode`, TalonAutomationMode>

/** One cap: its default (Q9), the customer's override (only lower) and the value in force. */
export interface TalonAutomationCap {
	default: number
	override: number | null
	effective: number
}

export interface TalonAutomationPolicy extends TalonAutomationModes {
	customer_code: string
	/** False while the customer has no row (every level `off`). */
	exists: boolean
	/** Level 2's admin-chosen catalogue artifacts. Not edited here yet; sent back unchanged. */
	level_2_artifacts: string[]
	/** Level 2's file allow globs per OS. Not edited here yet; sent back unchanged. */
	file_allow_globs: Record<string, string[]>
	caps: Record<string, TalonAutomationCap>
	risk_acknowledged_by: string | null
	risk_acknowledged_at: string | null
	updated_by: string | null
	updated_at: string | null
	version: number
}

export interface TalonAutomationPolicyResponse extends FlaskBaseResponse {
	policy: TalonAutomationPolicy
}

export interface TalonAutomationPolicyUpdate extends TalonAutomationModes {
	level_2_artifacts: string[]
	file_allow_globs: Record<string, string[]>
	/** Only the caps the admin lowered; a missing key or null means the default. */
	cap_overrides: Record<string, number | null>
	acknowledge_risk: boolean
	/** The version the admin edited: a concurrent change answers 409. */
	version: number
}

export interface TalonAutomationSettings extends FlaskBaseResponse {
	automation_enabled: boolean
	updated_by_user_id?: number | null
	updated_at?: string | null
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

/** The levels 3–4 this change raises (to a higher mode than they had): each needs the acknowledgement. */
export function riskRaises(before: TalonAutomationModes, after: TalonAutomationModes): TalonAutomationLevel[] {
	return RISK_LEVELS.filter(level => MODE_RANK[after[modeKey(level)]] > MODE_RANK[before[modeKey(level)]])
}

export function buildPolicyUpdate(
	policy: TalonAutomationPolicy,
	modes: TalonAutomationModes,
	capOverrides: Record<string, number | null>,
	acknowledgeRisk: boolean
): TalonAutomationPolicyUpdate {
	const overrides: Record<string, number | null> = {}
	for (const [key, value] of Object.entries(capOverrides)) {
		if (key in policy.caps) overrides[key] = value ?? null
	}
	return {
		...modesOf(modes),
		level_2_artifacts: [...policy.level_2_artifacts],
		file_allow_globs: { ...policy.file_allow_globs },
		cap_overrides: overrides,
		acknowledge_risk: acknowledgeRisk,
		version: policy.version
	}
}

export default {
	getPolicy(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<TalonAutomationPolicyResponse>(
			`/talon/v2/automation/${encodeURIComponent(customerCode)}`,
			{
				signal
			}
		)
	},
	putPolicy(customerCode: string, body: TalonAutomationPolicyUpdate) {
		return HttpClient.put<TalonAutomationPolicyResponse>(
			`/talon/v2/automation/${encodeURIComponent(customerCode)}`,
			body
		)
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
