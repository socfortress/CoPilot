import type { Alert } from "./alerts"
import type { CommentItem } from "./comments"

export interface CasesListResponse {
	cases: Case[]
	total: number
	open: number
	in_progress: number
	closed: number
	success: boolean
	message: string
}

export interface Case {
	id: number
	case_name: string
	case_description: string
	assigned_to: null | string
	alerts: Alert[]
	case_status: CaseStatus
	case_creation_time: Date
	customer_code: string
	notification_invoked_number: number
	escalated: boolean
	comments: CommentItem[]
}

export interface LinkedCase {
	case_name: string
	case_description: string
	case_creation_time: Date
	case_status: CaseStatus
	assigned_to: null | string
	id: number
}

export interface CasesFilters {
	assigned_to: string[]
	status: string[]
}

export interface CaseDataStoreFile {
	id: number
	case_id: number
	bucket_name: string
	object_key: string
	file_name: string
	content_type: string | null
	file_size: number | null
	upload_time: string
	file_hash: string
}

export type CaseStatus = "OPEN" | "IN_PROGRESS" | "CLOSED"
