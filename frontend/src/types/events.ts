import type { SafeAny } from "./common"

export interface EventSearchResult {
	[key: string]: SafeAny
}

export interface FieldMapping {
	field: string
	type: string
}
