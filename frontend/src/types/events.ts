import type { SafeAny } from "./common"

export type EventSearchResult = {
	_id?: string
	_index?: string
} & Record<string, SafeAny>

export interface FieldMapping {
	field: string
	type: string
}
