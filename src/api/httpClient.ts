import { useAuthStore } from "@/stores/auth"
import { isJwtExpiring } from "@/utils/auth"
import Api from "@/api"
import axios from "axios"
const BASE_URL = import.meta.env.VITE_API_URL

const HttpClient = axios.create({
	baseURL: BASE_URL
})

let __TOKEN_REFRESHING = false
let __TOKEN_ATTEMPTS: number[] = []
const TOKEN_MAX_ATTEMPTS = 3 // TODO: ?? replace with debounce time

HttpClient.interceptors.request.use(
	config => {
		const store = useAuthStore()

		if (!config.headers) config.headers = {}
		config.headers.Authorization = `Bearer ${store.userToken}`

		if (isJwtExpiring(store.userToken, 60 * 60) && !__TOKEN_REFRESHING) {
			__TOKEN_REFRESHING = true
			__TOKEN_ATTEMPTS.push(new Date().getTime())

			if (__TOKEN_ATTEMPTS.length >= TOKEN_MAX_ATTEMPTS) {
				window.location.href = "/logout"
			}

			Api.auth.refresh().then(res => {
				if (res.data.access_token) {
					store.setToken(res.data.access_token)

					__TOKEN_REFRESHING = false
					__TOKEN_ATTEMPTS = []
				}
			})
		}

		return config
	},
	error => Promise.reject(error)
)

// TODO: to complete
HttpClient.interceptors.response.use(
	response => response,
	error => {
		/*
		if (error.response) {
			if (error.response.status === 401 && !error.config.data?._retry) {
				if (!error.config.data) error.config.data = {}
				error.config.data._retry = true

				if (window.location.pathname.indexOf("login") === -1) {
					window.location.href = "/logout"
				}
			}
		}
		*/
		if (error.response && error.response.status === 401) {
			if (window.location.pathname.indexOf("login") === -1) {
				window.location.href = "/logout"
			}
		}

		return Promise.reject(error)
	}
)

export { HttpClient }
