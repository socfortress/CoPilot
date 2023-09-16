export type Role = "all" | "admin" | "moderator"
export type Roles = role | role[]

export interface RouteMetaAuth {
	checkAuth?: boolean
	authRedirect?: string
	auth?: boolean
	roles?: Roles
}
