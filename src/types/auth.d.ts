export type Role = "all" | "admin" | "moderator"
export type Roles = role | role[]

export interface RouteMetaAuth {
	checkAuth?: boolean
	authRedirect?: string
	auth?: boolean
	roles?: Roles
}

export interface LoginPayload {
	email: string
	password: string
}

export interface RegisterPayload {
	customerCode: string
	usersFirstName: string
	usersLastName: string
	usersEmail: string
	usersRole: string
	imageFile: string
	notifications: number
	password: string
}
