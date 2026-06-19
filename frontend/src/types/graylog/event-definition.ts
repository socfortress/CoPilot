export interface EventDefinition {
	alert: boolean
	config: EventDefinitionConfig
	description: string
	field_spec: { [key: string]: EventDefinitionFieldSpec }
	id: string
	key_spec: string[]
	notification_settings: {
		backlog_size: number
		grace_period_ms: number
	}
	notifications: EventDefinitionNotification[]
	priority: number
	storage: EventDefinitionStorage[]
	title: string
}

export interface EventDefinitionConfig {
	conditions: {
		expression: string | null
	}
	execute_every_ms: number
	group_by: string[]
	query: string
	query_parameters: string[]
	search_within_ms: number
	series:
		| string
		| {
				type: string
				id: string
				field: string
		  }[]
	streams: string[]
	type: string
}

export interface EventDefinitionFieldSpec {
	data_type: string
	providers: EventDefinitionProvider[]
}

export interface EventDefinitionProvider {
	require_values: boolean
	template: string
	type: string
}

export interface EventDefinitionNotification {
	notification_id: string
	notification_parameters: null
}

export interface EventDefinitionStorage {
	streams: string[]
	type: string
}
