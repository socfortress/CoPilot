import type { ScaOverviewQuery } from "@/types/sca"

export type ScaStreamingFilterType = "customer_codes" | "agent_name" | "policy_name" | "min_score" | "max_score"

export interface ScaStreamingListFilter {
	type: ScaStreamingFilterType
	/** ``customer_codes`` holds a list; every other filter is scalar. */
	value: string | string[] | number | null
}

export type ScaStreamingFilters = Pick<
	ScaOverviewQuery,
	"customer_codes" | "agent_name" | "policy_name" | "min_score" | "max_score"
>
