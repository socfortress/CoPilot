import type { Alert, AlertStatus } from "./alerts.d"

export interface Case {
	id: number
	case_name: string
	case_creation_time: string | Date
	case_description: string
	assigned_to: null | string
	alerts: Alert[]
	case_status: null | AlertStatus
}

export type CasePayload = Omit<Case, "id" | "alerts">
