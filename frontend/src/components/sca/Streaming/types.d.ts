import type { ScaOverviewQuery } from "@/types/sca"

export type ScaStreamingFilterType = "customer_code" | "agent_name" | "policy_name" | "min_score" | "max_score"

export interface ScaStreamingListFilter {
	type: ScaStreamingFilterType
	value: string | number | null
}

export type ScaStreamingFilters = Pick<
	ScaOverviewQuery,
	"customer_code" | "agent_name" | "policy_name" | "min_score" | "max_score"
>
