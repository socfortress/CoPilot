import type { PortalCustomer } from "@/types/auth"

/**
 * A customer admin's view of their customers' portal users (#1296): `/customer_portal/users`.
 * Times are naive UTC.
 */

export interface TenantUser {
	id: number
	username: string
	email: string
	/** Only the customers the caller administers: another customer is never named. */
	customers: PortalCustomer[]
	is_customer_admin: boolean
	disabled: boolean
	disabled_at: string | null
	must_change_password: boolean
	totp_enabled: boolean
	last_login_at: string | null
	is_self: boolean
	/** Whether the caller may disable, enable, reset 2FA or issue a temporary password. */
	can_manage: boolean
	/** Why not, when not: the caller, another admin, or an account shared with another customer. */
	managed_by_soc_reason: string | null
}

export interface TenantUsers {
	/** The customers the caller administers: the choices for an invitation. */
	customers: PortalCustomer[]
	users: TenantUser[]
	smtp_configured: boolean
}

export interface InvitePayload {
	username: string
	email: string
	customer_codes: string[]
}

/**
 * How a temporary password reached its user: emailed (never in the response), or `shown`: here,
 * once, for the caller to hand over, with `email_problem` saying why it did not go by email.
 */
export interface TemporaryPasswordDelivery {
	delivery: "email" | "shown"
	temporary_password: string | null
	email_problem: string | null
}

export interface TenantUserAction {
	user: TenantUser
}
