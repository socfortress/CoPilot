import type { AxiosRequestHeaders } from "axios"
import axios from "axios"
import { useAuthStore } from "@/stores/auth"

const httpClient = axios.create({
	baseURL: "/api"
})

let __TOKEN_REFRESHING = false
let __TOKEN_LAST_CHECK: Date | null = null

// Helper function to check if JWT is expiring
function isJwtExpiring(token: string | null, expiryThresholdSeconds: number): boolean {
	if (!token) return false

	try {
		const payload = JSON.parse(atob(token.split('.')[1]))
		const expiryTime = payload.exp * 1000 // Convert to milliseconds
		const currentTime = Date.now()
		const thresholdTime = expiryThresholdSeconds * 1000

		return (expiryTime - currentTime) <= thresholdTime
	} catch {
		return false
	}
}

// Helper function for debouncing token checks
function isDebounceTimeOver(lastCheck: Date | null): boolean {
	if (!lastCheck) return true
	return (Date.now() - lastCheck.getTime()) > 30000 // 30 seconds
}

httpClient.interceptors.request.use(
	config => {
		const store = useAuthStore()

		if (!config.headers) config.headers = {} as AxiosRequestHeaders
		if (store.userToken) {
			config.headers.Authorization = `Bearer ${store.userToken}`
		}

		if (isJwtExpiring(store.userToken, 60 * 60) && !__TOKEN_REFRESHING && isDebounceTimeOver(__TOKEN_LAST_CHECK)) {
			__TOKEN_REFRESHING = true
			__TOKEN_LAST_CHECK = new Date()

			store.refreshToken().then(() => {
				__TOKEN_REFRESHING = false
			}).catch(() => {
				__TOKEN_REFRESHING = false
			})
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
				const store = useAuthStore()
				store.logout()
				window.location.href = "/login"
			}
		}

		return Promise.reject(error)
	}
)

export { httpClient }
