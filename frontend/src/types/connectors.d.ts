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
	id: number
	name: string
	authToken?: null
	roles?: null
	response?: null
	history_logs: {
		id: number
		connector_id: number
		change_timestamp: string | Date
		change_description: string
	}[]
}

export enum ConnectorFormType {
	HOST = "host",
	TOKEN = "token",
	FILE = "file",
	CREDENTIALS = "credentials",
	UNKNOWN = "unknown"
}

export interface ConnectorFormOptions {
	extraData?: boolean
}

export type ConnectorFormOptionKeys = keyof ConnectorFormOptions

export interface ConnectorForm {
	connector_url: string
	connector_username: string
	connector_password: string
	connector_api_key: string
	connector_extra_data: string
	connector_file: File | null
}

export type ConnectorRequestPayload =
	| FormData
	| {
			connector_url?: string
			connector_username?: string
			connector_password?: string
			connector_api_key?: string
			connector_extra_data?: string
			/*eslint no-mixed-spaces-and-tabs: "off"*/
	  }

export enum ConnectorSupports {
	NotSpecified = "Not specified."
}
