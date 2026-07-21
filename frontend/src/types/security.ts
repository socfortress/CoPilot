export interface CustomerSecurityUser {
	id: number
	username: string
	email: string
	role_id?: number | null
	role_name?: string | null
	last_login_at?: string | null
	totp_enabled: boolean
}
