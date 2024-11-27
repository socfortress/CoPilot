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
	Analyst = 2
}

export type RouteMetaAuthRole = AuthUserRole | RouteRole

export interface JWTPayload extends jose.JWTPayload {
	scopes: JWTRole[]
}

export type JWTRole = "admin" | "analyst"

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
	/*
	customerCode: string
	usersFirstName: string
	usersLastName: string
	usersRole: "admin"
	imageFile: string
	notifications: number
	*/
}
