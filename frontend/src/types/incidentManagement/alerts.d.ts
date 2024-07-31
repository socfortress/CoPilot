export interface Alert {
	id: number
	alert_creation_time: Date
	alert_description: string
	alert_name: string
	assigned_to: null | string
	customer_code: string
	source: string
	status: AlertStatus
	time_closed: Date | null
	comments: AlertComment[]
	assets: AlertAsset[]
	tags: AlertTag[]
}

export type AlertStatus = "OPEN" | "CLOSED" | "IN_PROGRESS"

export interface AlertAsset {
	id: number
	agent_id: string
	alert_context_id: number
	alert_linked: number
	asset_name: string
	customer_code: string
	index_id: string
	index_name: string
	velociraptor_id: string
}

export interface AlertComment {
	id: number
	alert_id: number
	comment: string
	created_at: Date
	user_name: string
}

export interface AlertTag {
	id?: number
	tag: string
}

export interface AlertContext {
	id: number
	source: string
	context: AlertContextDetails
}

export interface AlertContextDetails {
	rule_description: string
	data_win_eventdata_image: string
	data_win_eventdata_parentImage: string
}
