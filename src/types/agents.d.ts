export interface Agents {
    agent_id: string
    client_id: string
    client_last_seen: string
    critical_asset: boolean
    hostname: string
    id?: number
    ip_address: string
    label: string
    last_seen: string
    os: string
    velociraptor_client_version: string
    wazuh_agent_version: string
}
