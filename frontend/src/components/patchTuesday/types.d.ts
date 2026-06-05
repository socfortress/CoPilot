import type { PatchTuesdayItem, PatchTuesdaySummary, PriorityLevel } from "@/types/patchTuesday.d"

export interface PatchTuesdayFilters {
	cycle: string | null
	priority: PriorityLevel | null
	family: string | null
	severity: string | null
	searchQuery: string | null
	kevOnly: boolean
}

export interface PatchTuesdayListEmits {
	(e: "item-click", item: PatchTuesdayItem): void
}

export interface PatchTuesdayStatsProps {
	summary: PatchTuesdaySummary | null
	loading?: boolean
}

export interface PatchTuesdayItemProps {
	item: PatchTuesdayItem
}
