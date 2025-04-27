export interface ExclusionRule {
	name: string
	description: string
	channel: string
	title: string
	field_matches: { [key: string]: string }
	customer_code: null | string
	enabled: boolean
	id: number
	created_by: string
	created_at: Date
	last_matched_at: Date | null
	match_count: number
}
