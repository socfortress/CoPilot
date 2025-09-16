import { httpClient } from '@/utils/httpClient'

export interface Alert {
  id: number
  alert_creation_time: string
  alert_description: string
  alert_name: string
  asset_name: string
  assigned_to: string | null
  case_ids: number[]
  customer_code: string
  index_id: string
  index_name: string
  source: string
  status: 'open' | 'in_progress' | 'closed'
  tag: string[]
  time_stamp: string
  comments?: AlertComment[]
}

export interface AlertComment {
  id: number
  alert_id: number
  comment: string
  user_name: string
  timestamp: string
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
  status: 'open' | 'in_progress' | 'closed'
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
  static async updateAlertStatus(alertId: number, status: 'open' | 'in_progress' | 'closed'): Promise<AlertResponse> {
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
  static async getAlertsByStatus(status: 'open' | 'in_progress' | 'closed'): Promise<AlertsResponse> {
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
