import type { FlaskBaseResponse } from "@/types/flask.d"
import type { CustomerNetworkConnector, NetworkConnector } from "@/types/networkConnectors.d"
import { HttpClient } from "../httpClient"

export interface NewNetworkConnector {
    customer_code: string
    customer_name: string
    network_connector_name: string
    network_connector_auth_keys: {
        auth_key_name: string
        auth_value: string
    }[]
}

export interface NewNetworkConnectorPayload extends NewNetworkConnector {
    network_connector_config: {
        auth_type: string
        config_key: string
        config_value: string
    }
}

export interface FortinetProvision {
    tcp_enabled: boolean
    udp_enabled: boolean
    hot_data_retention: number
    index_replicas: number
}

export interface FortinetProvisionPayload extends FortinetProvision {
    customer_code: string
    integration_name: string
}

export interface SonicwallProvision {
    tcp_enabled: boolean
    hot_data_retention: number
    index_replicas: number
}

export interface SonicwallProvisionPayload extends SonicwallProvision {
    customer_code: string
    integration_name: string
}

export interface SentinelOneProvision {
    tls_enabled: boolean
    hot_data_retention: number
    index_replicas: number
}

export interface SentinelOneProvisionPayload extends SentinelOneProvision {
    customer_code: string
    integration_name: string
}

export default {
    // #region Network Connector
    getAvailableNetworkConnectors() {
        return HttpClient.get<FlaskBaseResponse & { network_connector_keys: NetworkConnector[] }>(
            `/network_connectors/available_network_connectors`
        )
    },
    getCustomerNetworkConnectors(customerCode: string) {
        return HttpClient.get<FlaskBaseResponse & { available_network_connectors: CustomerNetworkConnector[] }>(
            `/network_connectors/customer_network_connectors/${customerCode}`
        )
    },
    createNetworkConnector(props: NewNetworkConnector) {
        const payload: NewNetworkConnectorPayload = {
            ...props,
            network_connector_config: {
                auth_type: "Fortinet",
                config_key: "firewall",
                config_value: "not applicable"
            }
        }
        return HttpClient.post<FlaskBaseResponse>(`/network_connectors/create_network_connector`, payload)
    },
    deleteNetworkConnector(customerCode: string, networkConnectorName: string) {
        return HttpClient.delete<FlaskBaseResponse>(`/network_connectors/delete_network_connector`, {
            data: { customer_code: customerCode, network_connector_name: networkConnectorName }
        })
    },
    decommissionNetworkConnector(customerCode: string, networkConnectorName: string) {
        return HttpClient.post<FlaskBaseResponse>(`/stack_decommissioning/graylog/decommission/network_connector`, {
            customer_code: customerCode,
            network_connector: networkConnectorName
        })
    },
    // #endregion

    // #region Provision
    fortinetProvision(customerCode: string, networkConnectorName: string, props: FortinetProvision) {
        const payload: FortinetProvisionPayload = {
            ...props,
            customer_code: customerCode,
            integration_name: networkConnectorName
        }
        return HttpClient.post<FlaskBaseResponse>(`/stack_provisioning/graylog/provision/fortinet`, payload)
    },
    sonicwallProvision(customerCode: string, networkConnectorName: string, props: SonicwallProvision) {
        const payload: SonicwallProvisionPayload = {
            ...props,
            customer_code: customerCode,
            integration_name: networkConnectorName
        }
        return HttpClient.post<FlaskBaseResponse>(`/stack_provisioning/graylog/provision/sonicwall`, payload)
    },
    sentineloneProvision(customerCode: string, networkConnectorName: string, props: SentinelOneProvision) {
        const payload: SentinelOneProvisionPayload = {
            ...props,
            customer_code: customerCode,
            integration_name: networkConnectorName
        }
        return HttpClient.post<FlaskBaseResponse>(`/stack_provisioning/graylog/provision/sentinelone`, payload)
    }
    // #endregion
}
