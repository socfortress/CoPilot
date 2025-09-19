import { httpClient } from '@/utils/httpClient'

export interface Case {
  id: number
  case_creation_time: string
  case_description: string
  case_name: string
  case_status: 'open' | 'in_progress' | 'closed'
  assigned_to: string | null
  customer_code: string
  alert_ids: number[]
  alerts?: Alert[]
}

export interface Alert {
  id: number
  alert_name: string
  asset_name: string
  status: 'open' | 'in_progress' | 'closed'
  time_stamp: string
}

export interface CasesResponse {
  cases: Case[]
  success: boolean
  message: string
}

export interface CaseResponse {
  cases: Case[]
  success: boolean
  message: string
}

export interface CaseStatusUpdate {
  case_id: number
  status: 'open' | 'in_progress' | 'closed'
}

export interface CaseAssignedToUpdate {
  case_id: number
  assigned_to: string
}

export interface CasePayload {
  case_name: string
  case_description: string
  assigned_to?: string
}

export class CasesAPI {
  /**
   * Get all cases with customer access control
   */
  static async getCases(): Promise<CasesResponse> {
    const response = await httpClient.get('/incidents/db_operations/cases')
    return response.data
  }

  /**
   * Get specific case by ID (with customer access validation)
   */
  static async getCase(caseId: number): Promise<CaseResponse> {
    const response = await httpClient.get(`/incidents/db_operations/case/${caseId}`)
    return response.data
  }

  /**
   * Update case status (customer access controlled)
   */
  static async updateCaseStatus(caseId: number, status: 'open' | 'in_progress' | 'closed'): Promise<CaseResponse> {
    const response = await httpClient.put('/incidents/db_operations/case/status', {
      case_id: caseId,
      status
    })
    return response.data
  }

  /**
   * Update case assigned user (customer access controlled)
   */
  static async updateCaseAssignedTo(caseId: number, assignedTo: string): Promise<CaseResponse> {
    const response = await httpClient.put('/incidents/db_operations/case/assigned-to', {
      case_id: caseId,
      assigned_to: assignedTo
    })
    return response.data
  }

  /**
   * Create new case (customer access controlled)
   */
  static async createCase(payload: CasePayload): Promise<{ case: Case; success: boolean; message: string }> {
    const response = await httpClient.post('/incidents/db_operations/case/create', payload)
    return response.data
  }

  /**
   * Delete case (customer access controlled)
   */
  static async deleteCase(caseId: number): Promise<{ success: boolean; message: string }> {
    const response = await httpClient.delete(`/incidents/db_operations/case/${caseId}`)
    return response.data
  }

  /**
   * Get cases by status with customer filtering
   */
  static async getCasesByStatus(status: string): Promise<CasesResponse> {
    const response = await httpClient.get(`/incidents/db_operations/case/status/${status}`)
    return response.data
  }

  /**
   * Get cases by assigned user with customer filtering
   */
  static async getCasesByAssignedTo(assignedTo: string): Promise<CasesResponse> {
    const response = await httpClient.get(`/incidents/db_operations/case/assigned-to/${assignedTo}`)
    return response.data
  }

  /**
   * Create case from alert (customer access controlled)
   */
  static async createCaseFromAlert(alertId: number): Promise<{ case_alert_link: { case_id: number; alert_id: number }; success: boolean; message: string }> {
    const response = await httpClient.post('/incidents/db_operations/case/from-alert', {
      alert_id: alertId
    })
    return response.data
  }

  /**
   * Link case to alert (customer access controlled)
   */
  static async linkCaseToAlert(caseId: number, alertId: number): Promise<{ case_alert_link: { case_id: number; alert_id: number }; success: boolean; message: string }> {
    const response = await httpClient.post('/incidents/db_operations/case/alert-link', {
      case_id: caseId,
      alert_id: alertId
    })
    return response.data
  }

  /**
   * Unlink case from alert (customer access controlled)
   */
  static async unlinkCaseFromAlert(caseId: number, alertId: number): Promise<{ success: boolean; message: string }> {
    const response = await httpClient.post('/incidents/db_operations/case/alert-unlink', {
      case_id: caseId,
      alert_id: alertId
    })
    return response.data
  }
}

export default CasesAPI
