import type { AxiosRequestHeaders } from "axios"
import axios from "axios"
import { useAuthStore } from "@/stores/auth"
import { isDebounceTimeOver, isJwtExpiring } from "@/utils/auth"
import { getNavigationSignal } from "./navigation-abort"
// import { useGlobalActions } from "@/composables/useGlobalActions"

declare module "axios" {
	interface AxiosRequestConfig {
		/**
		 * Keep this request alive across route changes. For calls that are not
		 * view-scoped — token refresh, licence gating, bootstrap lookups — where a
		 * cancellation would be read as a failure and change what the UI shows.
		 */
		keepOnNavigation?: boolean
		/** Set internally when the navigation scope owns this request's signal. */
		navigationScoped?: boolean
	}
}

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

		// Attach reads to the current route's scope so leaving the page cancels them.
		// Never mutations — aborting a POST/PUT/DELETE client-side does not undo it
		// server-side, it only hides whether it happened. A caller that supplied its
		// own signal keeps full ownership of its lifecycle.
		if (config.method?.toLowerCase() === "get" && !config.signal && !config.keepOnNavigation) {
			config.signal = getNavigationSignal()
			config.navigationScoped = true
		}

		if (
			store.userToken &&
			isJwtExpiring(store.userToken, 60 * 60) &&
			!__TOKEN_REFRESHING &&
			isDebounceTimeOver(__TOKEN_LAST_CHECK)
		) {
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
		// A request we cancelled because the user left the page is not an error the
		// user should hear about. Only ~40 components guard with `axios.isCancel`;
		// the other ~340 would pop an error toast on every navigation. Returning a
		// promise that never settles means their `.then`/`.catch`/`.finally` simply
		// never run — correct here, because the component asking is already gone.
		// Component-owned signals are untouched and still reject as before.
		if (axios.isCancel(error) && error.config?.navigationScoped) {
			return new Promise(() => {})
		}

		if (error.response && error.response.status === 401) {
			if (!window.location.pathname.includes("login")) {
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
