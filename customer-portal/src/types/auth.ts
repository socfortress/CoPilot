import type * as jose from "jose"

export interface RouteMetaAuth {
	checkAuth?: boolean
	authRedirect?: string
	auth?: boolean
	roles?: RouteMetaAuthRole | RouteMetaAuthRole[]
}

export enum RouteRole {
	All = "all"
}

export enum AuthUserRole {
	Unknown = "unknown",
	Admin = "admin",
	Analyst = "analyst",
	Superuser = "superuser"
}

export type RouteMetaAuthRole = AuthUserRole | RouteRole | string

/** A customer the portal user may see: the code is the key, the name is what to show. */
export interface PortalCustomer {
	customer_code: string
	customer_name: string
}

/** `GET /customer_portal/me`: read live, unlike the token's `customer_codes` claim. */
export interface PortalProfile {
	username: string
	role: string
	customers: PortalCustomer[]
	/** An admin chose the password and it has not been replaced yet (#1277). */
	must_change_password: boolean
}

export interface AuthUser {
	access_token: string | null
	role: AuthUserRole | string | null
	username: string | null
	/** From the token, until `GET /customer_portal/me` answers: see `stores/auth.ts`. */
	customer_codes: string[]
	/**
	 * An admin chose the password (a temporary one emailed, a reset, a new account): the
	 * portal holds the user on the change until they replace it (#1277).
	 */
	must_change_password?: boolean
}

/**
 * Shape of every token-issuing endpoint (`/auth/token/customer-portal`, `/auth/2fa/validate`,
 * `/auth/refresh`). There is no refresh token: a session is extended by calling
 * `GET /auth/refresh` with the still-valid access token (sliding expiry).
 */
export interface AuthResponse {
	access_token: string
	token_type: string
	/**
	 * Set by the login endpoint when the account has 2FA enabled. When true, `access_token`
	 * is a short-lived temp token to be exchanged at /auth/2fa/validate rather than a session.
	 */
	requires_2fa?: boolean
	/** Sent with a session token: the user must replace a password an admin chose (#1277). */
	must_change_password?: boolean
}

export interface JWTPayload extends jose.JWTPayload {
	scopes: string[]
	sub: string
	customer_codes: string[]
}
