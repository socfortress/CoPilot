import type { Alert, AlertStatus } from "./alerts.d"

export interface Case {
	id: number
	case_name: string
	case_creation_time: string | Date
	case_description: string
	assigned_to: null | string
	case_status: null | CaseStatus
	customer_code: null | string
	alerts: Alert[]
}

export type CaseStatus = AlertStatus

export type CasePayload = Omit<Case, "id" | "alerts">

export interface CaseDataStore {
	id: number
	case_id: number
	bucket_name: string
	object_key: string
	file_name: string
	content_type: string
	file_size: number
	upload_time: Date
	file_hash: string
}

export interface CaseReportTemplateDataStore {
	id: number
	report_template_name: string
	bucket_name: string
	object_key: string
	file_name: string
	content_type: string
	file_size: number
	upload_time: Date
	file_hash: string
}
