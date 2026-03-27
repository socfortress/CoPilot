export type FilterValuePrimitive = string | null | number | boolean
export type FilterValue = FilterValuePrimitive | FilterValuePrimitive[]

export interface FilterInfo {
	id: string
	label: string
	value: FilterValue
	options?: { label: string; value: FilterValuePrimitive }[]
	clearFilter: () => void
}
