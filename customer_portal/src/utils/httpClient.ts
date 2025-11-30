import type { AxiosRequestHeaders } from "axios"
import axios from "axios"

const httpClient = axios.create({
	baseURL: "/api"
})

let __TOKEN_REFRESHING = false
let __TOKEN_LAST_CHECK: Date | null = null

// Helper function to get token from localStorage
function getToken(): string | null {
	return localStorage.getItem("customer-portal-auth-token")
}

// Helper function to check if JWT is expiring
function isJwtExpiring(token: string | null, expiryThresholdSeconds: number): boolean {
	if (!token) return false

	try {
		const payload = JSON.parse(atob(token.split(".")[1]))
		const expiryTime = payload.exp * 1000 // Convert to milliseconds
		const currentTime = Date.now()
		const thresholdTime = expiryThresholdSeconds * 1000

		return expiryTime - currentTime <= thresholdTime
	} catch {
		return false
	}
}

// Helper function for debouncing token checks
function isDebounceTimeOver(lastCheck: Date | null): boolean {
	if (!lastCheck) return true
	return Date.now() - lastCheck.getTime() > 30000 // 30 seconds
}

httpClient.interceptors.request.use(
	config => {
		const token = getToken()

		if (!config.headers) config.headers = {} as AxiosRequestHeaders
		if (token) {
			config.headers.Authorization = `Bearer ${token}`
			console.log("Adding Authorization header:", `Bearer ${token.substring(0, 20)}...`)
		} else {
			console.warn("No token found in localStorage")
		}

		// Optional: Check for token expiry and handle refresh if needed
		if (isJwtExpiring(token, 60 * 60) && !__TOKEN_REFRESHING && isDebounceTimeOver(__TOKEN_LAST_CHECK)) {
			__TOKEN_REFRESHING = true
			__TOKEN_LAST_CHECK = new Date()

			// For customer portal, we'll just let the token expire and redirect to login
			// since customer users typically don't have refresh tokens
			console.warn("JWT token is expiring soon")
			__TOKEN_REFRESHING = false
		}

		return config
	},
	error => Promise.reject(error)
)

httpClient.interceptors.response.use(
	response => response,
	error => {
		if (error.response && error.response.status === 401) {
			if (!window.location.pathname.includes("login")) {
				// Clear stored auth data and redirect to login
				localStorage.removeItem("customer-portal-auth-token")
				localStorage.removeItem("customer-portal-user")
				window.location.href = "/login"
			}
		}

		return Promise.reject(error)
	}
)

export { httpClient }
