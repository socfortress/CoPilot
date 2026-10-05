import type { Asset } from "./assets"
import type { LinkedCase } from "./cases"
import type { CommentItem } from "./comments"
import type { Tag } from "./common"
import type { Ioc } from "./iocs"

export interface Alert {
	id: number
	alert_creation_time: Date
	time_closed: Date | null
	alert_name: string
	alert_description: string
	status: AlertStatus
	customer_code: string
	source: string
	assigned_to: null | string
	escalated: boolean
	time_stamp?: string
	index_id?: string
	index_name?: string
	asset_name?: string
	case_ids?: number[]
	comments: CommentItem[]
	assets: Asset[]
	tags: Tag[]
	tag?: string[]
	linked_cases: LinkedCase[]
	iocs: Ioc[]
}

export interface AlertsListResponse {
	alerts: Alert[]
	total: number
	open: number
	in_progress: number
	closed: number
	pending_customer?: number
}

/** `PENDING_CUSTOMER`: the SOC is waiting on the customer; the SLA clocks are stopped (#1187). */
export type AlertStatus = "OPEN" | "IN_PROGRESS" | "PENDING_CUSTOMER" | "CLOSED"

export interface AlertsFilters {
	sources: string[]
	assets: string[]
	tags: string[]
	statuses: string[]
}
