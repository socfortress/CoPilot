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

export interface AuthUser {
	access_token: string | null
	refresh_token: string | null
	role: AuthUserRole | string | null
	username: string | null
	customer_code: string | null
}

export interface AuthResponse {
	access_token: string
	refresh_token: string
	token_type: string
}

export interface JWTPayload extends jose.JWTPayload {
	scopes: string[]
	sub: string
	customer_codes: string[]
}
