export interface DashboardAlert {
	id: number
	name: string
	description: string
	severity: string
	created_at: string
}

export interface DashboardCase {
	id: number
	name: string
	description: string
	status: string
	created_at: string
	assigned_to?: string | null
}
