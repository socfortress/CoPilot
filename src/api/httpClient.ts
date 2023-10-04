import { useAuthStore } from "@/stores/auth"
import { isJwtExpiring } from "@/utils/auth"
import Api from "@/api"
import axios from "axios"
const BASE_URL = import.meta.env.VITE_API_URL

const store = useAuthStore()

const HttpClient = axios.create({
	baseURL: BASE_URL
})

HttpClient.interceptors.request.use(config => {
	if (!config.headers) config.headers = {}
	config.headers.token = store.user.token

	if (isJwtExpiring(store.user.token, 60 * 60)) {
		Api.auth.refresh().then(res => {
			if (res.data.success && res.data.token) {
				store.setToken(res.data.token)
			}
		})
	}

	return config
})

// TODO: to complete
HttpClient.interceptors.response.use(
	response => {
		//if (response.config?.data?._retry) response.config.data._retry = false

		return response
	},
	error => {
		if (error.response) {
			if (error.response.status === 401 && !error.config.data?._retry) {
				if (!error.config.data) error.config.data = {}
				//error.config.data._retry = true

				if (window.location.pathname.indexOf("login") === -1) {
					window.location.href = "/logout"
				}
			}
		}

		return Promise.reject(error)
	}
)

export { HttpClient }
