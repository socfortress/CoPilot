export interface DashboardAlert {
	id: number
	name: string
	description: string
	severity: string
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
