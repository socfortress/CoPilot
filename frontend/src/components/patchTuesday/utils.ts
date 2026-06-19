import type { PatchTuesdayFilters, PatchTuesdayListFilter } from "./types.d"
import type { PriorityLevel } from "@/types/patchTuesday"

export function patchTuesdayListToFilters(list: PatchTuesdayListFilter[]): PatchTuesdayFilters {
	return {
		cycle: (list.find(filter => filter.type === "cycle")?.value as string | null) ?? null,
		priority: (list.find(filter => filter.type === "priority")?.value as PriorityLevel | null) ?? null,
		family: (list.find(filter => filter.type === "family")?.value as string | null) ?? null,
		severity: (list.find(filter => filter.type === "severity")?.value as string | null) ?? null,
		searchQuery: (list.find(filter => filter.type === "searchQuery")?.value as string | null) ?? null,
		kevOnly: list.find(filter => filter.type === "kevOnly")?.value === true
	}
}
