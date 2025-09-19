import type { ScaOverviewQuery } from "@/types/sca.d"

export type ScaOverviewFilterTypes = keyof Omit<ScaOverviewQuery, "page" | "page_size">

export interface ScaOverviewFilter {
	type: ScaOverviewFilterTypes
	value: string | number | null
}
