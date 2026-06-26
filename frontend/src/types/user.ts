export interface User {
	id: number
	username: string
	email: string
	role_id?: number
	role_name?: string
	assigned_tags?: number[]
}
