import { useAuthStore } from "@/stores/auth"
import { isDebounceTimeOver, isJwtExpiring } from "@/utils/auth"
import Api from "@/api"
import axios from "axios"
import { useGlobalActions } from "@/composables/useGlobalActions"

const BASE_URL = import.meta.env.VITE_API_URL

const HttpClient = axios.create({
	baseURL: BASE_URL
})

let __TOKEN_REFRESHING = false
let __TOKEN_LAST_CHECK: Date | null = null

HttpClient.interceptors.request.use(
	config => {
		const store = useAuthStore()

		if (!config.headers) config.headers = {}
		config.headers.Authorization = `Bearer ${store.userToken}`

		if (isJwtExpiring(store.userToken, 60 * 60) && !__TOKEN_REFRESHING && isDebounceTimeOver(__TOKEN_LAST_CHECK)) {
			__TOKEN_REFRESHING = true
			__TOKEN_LAST_CHECK = new Date()

			Api.auth.refresh().then(res => {
				if (res.data.access_token) {
					store.setToken(res.data.access_token)

					__TOKEN_REFRESHING = false
				}
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
			useGlobalActions().message("You are not authorized to access the resource", { type: "error" })
		}

		return Promise.reject(error)
	}
)

export { HttpClient }
