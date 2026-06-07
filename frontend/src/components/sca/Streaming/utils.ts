import type { ScaStreamingFilters, ScaStreamingListFilter } from "./types.d"

export function scaStreamingListToFilters(list: ScaStreamingListFilter[]): ScaStreamingFilters {
	const customerCode = list.find(filter => filter.type === "customer_code")?.value
	const agentName = list.find(filter => filter.type === "agent_name")?.value
	const policyName = list.find(filter => filter.type === "policy_name")?.value
	const minScore = list.find(filter => filter.type === "min_score")?.value
	const maxScore = list.find(filter => filter.type === "max_score")?.value

	return {
		customer_code: typeof customerCode === "string" && customerCode ? customerCode : undefined,
		agent_name: typeof agentName === "string" && agentName ? agentName : undefined,
		policy_name: typeof policyName === "string" && policyName ? policyName : undefined,
		min_score: typeof minScore === "number" ? minScore : undefined,
		max_score: typeof maxScore === "number" ? maxScore : undefined
	}
}
