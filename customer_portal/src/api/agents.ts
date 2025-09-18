import { httpClient } from '@/utils/httpClient'

export interface Agent {
  id: number
  agent_id: string
  ip_address: string
  os: string
  hostname: string
  label: string
  critical_asset: boolean
  wazuh_last_seen: string
  velociraptor_id: string | null
  velociraptor_last_seen: string | null
  wazuh_agent_version: string
  wazuh_agent_status: string
  velociraptor_agent_version: string | null
  customer_code: string
  quarantined: boolean
  velociraptor_org: string | null
}

export interface AgentsResponse {
  agents: Agent[]
  success: boolean
  message: string
}

class AgentsAPI {
  /**
   * Get all agents for the authenticated customer
   */
  async getAgents(): Promise<AgentsResponse> {
    try {
      const response = await httpClient.get('/agents')
      return response.data
    } catch (error: any) {
      console.error('Error fetching agents:', error)
      throw error
    }
  }

  /**
   * Get a specific agent by ID
   */
  async getAgentById(agentId: string): Promise<{ agent: Agent; success: boolean; message: string }> {
    try {
      const response = await httpClient.get(`/agents/${agentId}`)
      return response.data
    } catch (error: any) {
      console.error('Error fetching agent:', error)
      throw error
    }
  }

  /**
   * Get agent by hostname
   */
  async getAgentByHostname(hostname: string): Promise<{ agent: Agent; success: boolean; message: string }> {
    try {
      const response = await httpClient.get(`/agents/hostname/${hostname}`)
      return response.data
    } catch (error: any) {
      console.error('Error fetching agent by hostname:', error)
      throw error
    }
  }

  /**
   * Mark agent as critical
   */
  async markAgentAsCritical(agentId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await httpClient.post(`/agents/${agentId}/critical`)
      return response.data
    } catch (error: any) {
      console.error('Error marking agent as critical:', error)
      throw error
    }
  }

  /**
   * Mark agent as not critical
   */
  async markAgentAsNotCritical(agentId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await httpClient.post(`/agents/${agentId}/noncritical`)
      return response.data
    } catch (error: any) {
      console.error('Error marking agent as not critical:', error)
      throw error
    }
  }
}

export default new AgentsAPI()