export interface Agent {
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
    vulnerabilities?: AgentVulnerabilities[]
    online?: boolean
}

export interface AgentVulnerabilities {
    id?: string
    architecture: string
    condition: string
    cve: string
    cvss2_score: number
    cvss3_score: number
    detection_time: string
    external_references: string[]
    name: string
    published: string
    severity: VulnerabilitySeverity
    status: VulnerabilityStatus
    title: string
    type: VulnerabilityType
    updated: string
    version: string
}

export enum VulnerabilitySeverity {
    Critical = "Critical",
    High = "High",
    Low = "Low",
    Medium = "Medium",
    Untriaged = "Untriaged"
}

export enum VulnerabilityStatus {
    Valid = "VALID"
}

export enum VulnerabilityType {
    Package = "PACKAGE"
}

export type OutdatedWazuhAgents = Agent[]

export type OutdatedVelociraptorAgents = Agent[]
