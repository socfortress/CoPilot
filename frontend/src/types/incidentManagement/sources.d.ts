export type SourceName = string

export interface SourceConfiguration {
	field_names: string[]
	asset_name: string
	timefield_name: string
	alert_title_name: string
	source: string
	ioc_field_names: string[]
}

export interface SourceConfigurationModel extends SourceConfiguration {
	index_name?: string | null
	asset_name: string | null
	timefield_name: string | null
	alert_title_name: string | null
	source: string | null
}

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
