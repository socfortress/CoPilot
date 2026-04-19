export interface User {
	email: string
	username: string
	full_name: string
	customer_id: number | null
	id: number
	is_active: boolean
	created_at: Date
	updated_at: Date
	last_login: Date
}
