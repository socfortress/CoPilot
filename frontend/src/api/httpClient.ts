import { useAuthStore } from "@/stores/auth"
import { isDebounceTimeOver, isJwtExpiring } from "@/utils/auth"
import axios, { type AxiosRequestHeaders } from "axios"
// import { useGlobalActions } from "@/composables/useGlobalActions"

const HttpClient = axios.create({
	baseURL: "/api"
})

let __TOKEN_REFRESHING = false
let __TOKEN_LAST_CHECK: Date | null = null

HttpClient.interceptors.request.use(
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
			})
		}

		return config
	},
	error => Promise.reject(error)
)

HttpClient.interceptors.response.use(
	response => response,
	error => {
		if (error.response && error.response.status === 401) {
			if (window.location.pathname.indexOf("login") === -1) {
				window.location.href = "/logout"
			}
			/*
			useGlobalActions().message("You are not authorized to access the resource", { type: "error" })
			*/
		}

		return Promise.reject(error)
	}
)

export { HttpClient }
