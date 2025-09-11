export interface AgentScaOverviewItem {
	agent_id: string
	agent_name: string
	customer_code?: string | null
	policy_id: string
	policy_name: string
	description: string
	total_checks: number
	pass_count: number
	fail_count: number
	invalid_count: number
	score: number
	start_scan: string
	end_scan: string
	references?: string | null
	hash_file?: string | null
}

export interface ScaOverviewResponse {
	sca_results: AgentScaOverviewItem[]
	total_count: number
	total_agents: number
	total_policies: number
	average_score: number
	total_checks_all_agents: number
	total_passes_all_agents: number
	total_fails_all_agents: number
	total_invalid_all_agents: number
	page: number
	page_size: number
	total_pages: number
	has_next: boolean
	has_previous: boolean
	success: boolean
	message: string
	filters_applied: Record<string, any>
}

export interface ScaOverviewQuery {
	customer_code?: string
	agent_name?: string
	policy_id?: string
	policy_name?: string
	min_score?: number
	max_score?: number
	page?: number
	page_size?: number
}

export interface ScaStatsResponse {
	total_agents_with_sca: number
	total_policies: number
	average_score_across_all: number
	total_checks_all_agents: number
	total_passes_all_agents: number
	total_fails_all_agents: number
	total_invalid_all_agents: number
	by_customer: Record<string, {
		total_agents: number
		total_policies: number
		average_score: number
		total_checks: number
		total_passes: number
		total_fails: number
		total_invalid: number
	}>
	success: boolean
	message: string
}

export enum ScaComplianceLevel {
	Excellent = "Excellent", // 90-100%
	Good = "Good", // 80-89%
	Average = "Average", // 70-79%
	Poor = "Poor", // 60-69%
	Critical = "Critical" // <60%
}

export function getComplianceLevel(score: number): ScaComplianceLevel {
	if (score >= 90) return ScaComplianceLevel.Excellent
	if (score >= 80) return ScaComplianceLevel.Good
	if (score >= 70) return ScaComplianceLevel.Average
	if (score >= 60) return ScaComplianceLevel.Poor
	return ScaComplianceLevel.Critical
}

export function getComplianceLevelColor(level: ScaComplianceLevel): "primary" | "warning" | "success" | "danger" {
	switch (level) {
		case ScaComplianceLevel.Excellent:
			return "success"
		case ScaComplianceLevel.Good:
			return "primary"
		case ScaComplianceLevel.Average:
			return "warning"
		case ScaComplianceLevel.Poor:
			return "warning"
		case ScaComplianceLevel.Critical:
			return "danger"
		default:
			return "primary"
	}
}

export function getComplianceLevelIcon(level: ScaComplianceLevel): string {
	switch (level) {
		case ScaComplianceLevel.Excellent:
			return "carbon:checkmark-filled"
		case ScaComplianceLevel.Good:
			return "carbon:checkmark"
		case ScaComplianceLevel.Average:
			return "carbon:warning-alt"
		case ScaComplianceLevel.Poor:
			return "carbon:warning"
		case ScaComplianceLevel.Critical:
			return "carbon:warning-filled"
		default:
			return "carbon:help"
	}
}
