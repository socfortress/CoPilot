export interface User {
	id: number
	username: string
	email: string
	role_id?: number
	role_name?: string
	assigned_tags?: number[]
	last_login_at?: string | null
	/** Assigned customers: only in the admin's user list (#1219). */
	customer_codes?: string[] | null
}
