export interface RouteMetaAuth {
	checkAuth?: boolean
	authRedirect?: string
	auth?: boolean
	roles?: UserRole | UserRole[]
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

export enum UserRole {
	All = "all",
	Unknown = 0,
	Admin = 1,
	Analyst = 2
}

export interface User {
	access_token: string
	role: UserRole
	username: string
	email: string
}

export interface AuthUser {
	id: number
	username: string
	email: string
}
