export interface AvailableIntegration {
	id: number
	integration_name: string
	description: string
	integration_details: string
	auth_keys: IntegrationAuthKey[]
}

export interface IntegrationAuthKey {
	auth_key_name: string
}

export interface CustomerIntegration {
	customer_code: string
	id: number
	deployed: boolean
	customer_name: string
	integration_service_id: number
	integration_service_name: string
	integration_subscriptions: IntegrationSubscription[]
}

export interface IntegrationSubscription {
	id: number
	customer_id: number
	integration_service_id: number
	integration_service: IntegrationService
	integration_auth_keys: IntegrationAuthKeyFull[]
}

export interface IntegrationAuthKeyFull {
	id: number
	auth_key_name: string
	auth_value: string
	subscription_id: number
}

export interface IntegrationService {
	auth_type: string
	service_name: string
	id: number
}

export interface CustomerIntegrationMetaCommon {
	id: number
	customer_code: string
	graylog_input_id?: string
	graylog_index_id?: string
	graylog_stream_id?: string
	graylog_pipeline_id?: string
	graylog_content_pack_input_id?: string
	graylog_content_pack_stream_id?: string
	grafana_org_id?: string
	grafana_dashboard_folder_id?: string
	grafana_datasource_uid?: string
}

export interface CustomerIntegrationMetaThirdParty extends CustomerIntegrationMetaCommon {
	integration_name: string
}

export interface CustomerIntegrationMetaNetwork extends CustomerIntegrationMetaCommon {
	network_connector_name: string
}

export type CustomerIntegrationMetaResponse =
	| {
			data: CustomerIntegrationMetaThirdParty
			table_type: "integration"
	  }
	| {
			data: CustomerIntegrationMetaNetwork
			table_type: "network_connector"
	  }
