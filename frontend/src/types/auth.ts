import type { JWTPayload as JoseJWTPayload } from "jose"

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
	Unknown = 0,
	Admin = 1,
	Analyst = 2,
	Scheduler = 3,
	CustomerUser = 4,
	/** An analyst who may also run response actions, on their assigned customers only (#1219). */
	Responder = 5
}

export type RouteMetaAuthRole = AuthUserRole | RouteRole

export interface JWTPayload extends JoseJWTPayload {
	scopes: JWTRole[]
}

export type JWTRole = "admin" | "analyst" | "responder"

export interface AuthUser {
	access_token: string
	role: AuthUserRole
	username: string
	email: string
}

export interface LoginPayload {
	username: string
	password: string
}

export interface RegisterPayload {
	username: string
	password: string
	email: string
	role_id: number
	/** Required for an analyst or responder (#1219). */
	customer_codes?: string[]
	/*
	customerCode: string
	usersFirstName: string
	usersLastName: string
	usersRole: "admin"
	imageFile: string
	notifications: number
	*/
}
