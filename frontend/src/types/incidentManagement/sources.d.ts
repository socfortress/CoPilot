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
	asset_name_array?: string[]
	timefield_name: string | null
	alert_title_name: string | null
	source: string | null
}
