import type { AxiosInstance, AxiosRequestHeaders } from "axios"
import axios from "axios"
import { useAuthStore } from "@/stores/auth"
import { isDebounceTimeOver, isJwtExpiring } from "@/utils/auth"
import { anySignal, getNavigationSignal } from "./navigation-abort"
// import { useGlobalActions } from "@/composables/common/useGlobalActions"

declare module "axios" {
	interface AxiosRequestConfig {
		/**
		 * Keep this request alive across route changes: for calls that are not
		 * page-scoped (branding, token refresh, cached lookups, the report poller,
		 * downloads), where a cancellation would read as a failure. See navigation-abort.ts.
		 */
		keepOnNavigation?: boolean
		/** Set internally: the route scope this request was attached to. */
		navigationSignal?: AbortSignal
	}
}

type HttpClientBase = "api" | "ws"

const DEFAULT_API_ROOT = "/api"
const API_ROOT = import.meta.env.VITE_API_ROOT || DEFAULT_API_ROOT
const WS_ROOT = import.meta.env.VITE_WS_ROOT || API_ROOT

let __TOKEN_REFRESHING = false
let __TOKEN_LAST_CHECK: Date | null = null

function applyInterceptors(client: AxiosInstance) {
	client.interceptors.request.use(
		config => {
			const store = useAuthStore()

			if (!config.headers) config.headers = {} as AxiosRequestHeaders
			if (store.userToken) {
				config.headers.Authorization = `Bearer ${store.userToken}`
			}

			// Attach reads to the current route's scope so leaving the page cancels them,
			// alongside any signal the caller brought. Never mutations: aborting one
			// client-side does not undo it server-side, it only hides whether it happened.
			if (config.method?.toLowerCase() === "get" && !config.keepOnNavigation) {
				const navigationSignal = getNavigationSignal()
				const own = config.signal as AbortSignal | undefined
				config.signal = own ? anySignal([own, navigationSignal]) : navigationSignal
				config.navigationSignal = navigationSignal
			}

			// An already-expired token cannot be refreshed (the backend rejects it); the
			// router guard logs the user out instead, so don't fire a doomed 401.
			if (
				store.userToken &&
				isJwtExpiring(store.userToken, 60 * 15 /** 15 minutes */) &&
				!isJwtExpiring(store.userToken, 0) &&
				!__TOKEN_REFRESHING &&
				isDebounceTimeOver(__TOKEN_LAST_CHECK)
			) {
				__TOKEN_REFRESHING = true
				__TOKEN_LAST_CHECK = new Date()

				// Fire-and-forget: this request still goes out with the old (valid) token.
				// A failed refresh must release the flag or no further attempt is ever made;
				// the debounce above keeps a persistently failing backend from being hammered.
				store
					.refreshToken()
					.catch(() => {})
					.finally(() => {
						__TOKEN_REFRESHING = false
					})
			}

			return config
		},
		error => Promise.reject(error)
	)

	client.interceptors.response.use(
		response => response,
		error => {
			// A request cancelled because the user left the page is not an error anyone
			// should hear about: the component that asked is gone. A promise that never
			// settles skips its `.catch` (no error toast) and its `.finally` (nothing left
			// to update). A cancellation the caller made itself still rejects as before.
			if (axios.isCancel(error) && error.config?.navigationSignal?.aborted) {
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
}

function createHttpClient(baseURL: string) {
	const client = axios.create({ baseURL })
	applyInterceptors(client)
	return client
}

const HttpClient = createHttpClient(API_ROOT)
const WsHttpClient = createHttpClient(WS_ROOT)

const CLIENTS: Record<HttpClientBase, AxiosInstance> = {
	api: HttpClient,
	ws: WsHttpClient
}

function getHttpClient(base: HttpClientBase = "api") {
	return CLIENTS[base]
}

export { API_ROOT, createHttpClient, getHttpClient, HttpClient, WsHttpClient }
