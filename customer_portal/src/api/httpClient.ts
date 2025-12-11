import type { AxiosRequestHeaders } from "axios"
import axios from "axios"
import { useAuthStore } from "@/stores/auth"
import { isDebounceTimeOver, isJwtExpiring } from "@/utils/auth"

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
        if (error.response) {
            const status = error.response.status

            if (status === 401) {
                // Unauthorized - authentication failed (invalid/expired token)
                if (!window.location.pathname.includes("login")) {
                    window.location.href = "/logout"
                }
            } else if (status === 403) {
                // Forbidden - insufficient permissions (keep user logged in)
                if (!window.location.pathname.includes("access-denied")) {
                    const message = error.response.data?.detail || "You do not have permission to access this resource."
                    window.location.href = `/access-denied?message=${encodeURIComponent(message)}`
                }
            }
        }

        return Promise.reject(error)
    }
)

export { HttpClient }
