import type { AlertStatus } from "@/types/alerts"

export interface DashboardAlert {
	id: number
	name: string
	description: string
	/** The alert's real workflow status. There is no severity on a CoPilot alert. */
	status: AlertStatus
	tags: string[]
	created_at: string | Date
}

export interface DashboardCase {
	id: number
	name: string
	description: string
	status: string
	created_at: string | Date
	assigned_to?: string | null
}
