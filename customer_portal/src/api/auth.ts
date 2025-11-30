import { httpClient } from "@/utils/httpClient"

export interface LoginCredentials {
	username: string
	password: string
}

export interface TokenResponse {
	access_token: string
	token_type: string
}

export interface DecodedToken {
	username: string
	scopes: string[]
	exp?: number
	sub?: string
}

export class AuthAPI {
	/**
	 * Login with username and password
	 */
	static async login(credentials: LoginCredentials): Promise<TokenResponse> {
		const formData = new URLSearchParams()
		formData.append("username", credentials.username)
		formData.append("password", credentials.password)

		const response = await httpClient.post("/auth/token/customer-portal", formData, {
			headers: {
				"Content-Type": "application/x-www-form-urlencoded"
			}
		})
		return response.data
	}

	/**
	 * Decode JWT token to extract user information
	 */
	static decodeToken(token: string): DecodedToken | null {
		try {
			const payload = JSON.parse(atob(token.split(".")[1]))
			return {
				username: payload.sub || "",
				scopes: payload.scopes || [],
				exp: payload.exp,
				sub: payload.sub
			}
		} catch (err) {
			console.error("Failed to decode token:", err)
			return null
		}
	}

	/**
	 * Validate if user has customer_user scope
	 */
	static hasCustomerAccess(scopes: string[]): boolean {
		return scopes.includes("customer_user")
	}
}

export default AuthAPI
