export interface Connector {
	clusterHealth?: null
	connectionSuccessful: boolean
	connector_accepts_api_key: boolean
	connector_accepts_host_only: boolean
	connector_accepts_file: boolean
	connector_accepts_username_password: boolean
	connector_accepts_extra_data: boolean
	connector_api_key?: string
	connector_configured: boolean
	connector_description?: string
	connector_extra_data?: string
	connector_last_updated: string
	connector_name: string
	connector_password?: string
	connector_supports?: string
	connector_type: string
	connector_url: string
	connector_username?: string
	connector_verified: boolean
	connector_supports: ConnectorSupports | string
	// TODO: to verify connector_file prop
	connector_file: string
	id: number
	name: string
	authToken?: null
	roles?: null
	response?: null
	history_logs: any[]
}

export enum ConnectorFormType {
	TOKEN = "token",
	FILE = "file",
	CREDENTIALS = "credentials",
	UNKNOWN = "unknown"
}

export interface ConnectorForm {
	connector_url: string
	connector_username: string
	connector_password: string
	connector_api_key: string
	connector_file: File | null
}

export interface ConnectorRequestPayload {
	connector_url: string
	connector_username?: string
	connector_password?: string
	connector_api_key?: string
}

export enum ConnectorSupports {
	NotSpecified = "Not specified."
}
