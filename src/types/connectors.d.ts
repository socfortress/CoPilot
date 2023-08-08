export interface Connector {
    clusterHealth?: null
    connectionSuccessful: boolean
    connector_accepts_api_key: boolean
    connector_accepts_file: boolean
    connector_accepts_username_password: boolean
    connector_api_key: string
    connector_configured: boolean
    connector_description: string
    connector_last_updated: string
    connector_name: string
    connector_password: string
    connector_supports: string
    connector_type: string
    connector_url: string
    connector_username: string
    connector_verified: boolean
    id: number
    name: string
    authToken?: null
    roles?: null
    response?: null
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
    connector_file: string
}
