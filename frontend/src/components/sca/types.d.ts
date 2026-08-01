import type { ScaOverviewQuery } from "@/types/sca"

export type ScaOverviewFilterTypes = keyof Omit<ScaOverviewQuery, "page" | "page_size">

export interface ScaOverviewFilter {
	type: ScaOverviewFilterTypes
	/** ``customer_codes`` holds a list; every other filter is scalar. */
	value: string | string[] | number | null
}
