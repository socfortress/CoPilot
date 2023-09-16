import axios from "axios"
const BASE_URL = import.meta.env.VITE_API_URL

export const HttpClient = axios.create({
    baseURL: BASE_URL
    // timeout: 2000,
    // headers: { "api-key": API_KEY }
})

// TODO: To be set when the authentication mechanism is implemented
/*
HttpClient.interceptors.response.use(
    response => {
        return response
    },
    error => {
        if (error.status === 401 || error.status === 412 || error.status === 409) {
            if (window.location.pathname.indexOf("login") === -1) {
                window.location.href = "/logout"
            }
        }

        return Promise.reject(error)
    }
)
*/
