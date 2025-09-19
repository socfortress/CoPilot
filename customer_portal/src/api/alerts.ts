import { httpClient } from '@/utils/httpClient'

export interface AlertComment {
  id: number
  alert_id: number
  comment: string
  user_name: string
  created_at: string
}

export interface AlertAsset {
  id: number
  asset_name: string
  agent_id: string
  customer_code: string
  index_id: string
  alert_linked: number
  alert_context_id: number
  velociraptor_id: string
  index_name: string
}

export interface AlertTag {
  id: number
  tag: string
}

export interface AlertIoC {
  id: number
  ioc_value: string
  ioc_type: string
  ioc_description: string
}

export interface LinkedCase {
  id: number
  case_name: string
  case_description: string
  case_creation_time: string
  case_status: string
  assigned_to: string | null
}

export interface Alert {
  id: number
  alert_creation_time: string
  time_closed: string | null
  alert_name: string
  alert_description: string
  status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED'
  customer_code: string
  source: string
  assigned_to: string | null
  time_stamp?: string
  index_id?: string
  index_name?: string
  asset_name?: string
  case_ids?: number[]
  tag?: string[]
  comments: AlertComment[]
  assets: AlertAsset[]
  tags: AlertTag[]
  linked_cases: LinkedCase[]
  iocs: AlertIoC[]
}

export interface AlertsResponse {
  alerts: Alert[]
  total: number
  open: number
  in_progress: number
  closed: number
  success: boolean
  message: string
}

export interface AlertResponse {
  alerts: Alert[]
  success: boolean
  message: string
}

export interface AlertStatusUpdate {
  alert_id: number
  status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED'
}

export interface AlertCommentPayload {
  alert_id: number
  comment: string
  user_name: string
}

export class AlertsAPI {
  /**
   * Get all alerts with customer access control
   */
  static async getAlerts(
    page: number = 1,
    pageSize: number = 25,
    order: 'asc' | 'desc' = 'desc'
  ): Promise<AlertsResponse> {
    const response = await httpClient.get('/incidents/db_operations/alerts', {
      params: {
        page,
        page_size: pageSize,
        order
      }
    })
    return response.data
  }

  /**
   * Get specific alert by ID (with customer access validation)
   */
  static async getAlert(alertId: number): Promise<AlertResponse> {
    const response = await httpClient.get(`/incidents/db_operations/alert/${alertId}`)
    return response.data
  }

  /**
   * Update alert status (customer access controlled)
   */
  static async updateAlertStatus(alertId: number, status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED'): Promise<AlertResponse> {
    const response = await httpClient.put('/incidents/db_operations/alert/status', {
      alert_id: alertId,
      status
    })
    return response.data
  }

  /**
   * Add comment to alert (customer access controlled)
   */
  static async addComment(payload: AlertCommentPayload): Promise<{ comment: AlertComment; success: boolean; message: string }> {
    const response = await httpClient.post('/incidents/db_operations/alert/comment', payload)
    return response.data
  }

  /**
   * Delete alert comment (customer access controlled)
   */
  static async deleteComment(commentId: number): Promise<{ success: boolean; message: string }> {
    const response = await httpClient.delete(`/incidents/db_operations/alert/comment/${commentId}`)
    return response.data
  }

  /**
   * Get alerts by status with customer filtering
   */
  static async getAlertsByStatus(status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED'): Promise<AlertsResponse> {
    const response = await httpClient.get(`/incidents/db_operations/alerts/status/${status}`)
    return response.data
  }

  /**
   * Get alerts by asset name with customer filtering
   */
  static async getAlertsByAsset(assetName: string): Promise<AlertsResponse> {
    const response = await httpClient.get(`/incidents/db_operations/alerts/asset/${assetName}`)
    return response.data
  }

  /**
   * Get alerts by source with customer filtering
   */
  static async getAlertsBySource(source: string): Promise<AlertsResponse> {
    const response = await httpClient.get(`/incidents/db_operations/alerts/source/${source}`)
    return response.data
  }
}

export default AlertsAPI
