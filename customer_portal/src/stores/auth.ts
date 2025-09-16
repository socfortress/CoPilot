import { defineStore } from 'pinia'
import axios from 'axios'

interface User {
	id: number
	username: string
	email: string
	role_id?: number
	role_name?: string
}

interface AuthState {
	userToken: string | null
	user: User | null
	isAuthenticated: boolean
}

export const useAuthStore = defineStore('auth', {
	state: (): AuthState => ({
		userToken: null,
		user: null,
		isAuthenticated: false
	}),

	getters: {
		isLogged: (state) => state.isAuthenticated && !!state.userToken,
		isCustomerUser: (state) => state.user?.role_name === 'customer_user'
	},

	actions: {
		async login(username: string, password: string) {
			try {
				const formData = new FormData()
				formData.append('username', username)
				formData.append('password', password)

				const response = await axios.post('/api/auth/token', formData)

				if (response.data.access_token) {
					this.userToken = response.data.access_token
					this.isAuthenticated = true
					await this.fetchUser()
					return { success: true }
				}

				return { success: false, message: 'Login failed' }
			} catch (error: any) {
				return {
					success: false,
					message: error.response?.data?.detail || 'Login failed'
				}
			}
		},

		async fetchUser() {
			try {
				const response = await axios.get('/api/auth/me', {
					headers: {
						Authorization: `Bearer ${this.userToken}`
					}
				})
				this.user = response.data
			} catch (error) {
				console.error('Failed to fetch user:', error)
			}
		},

		async refreshToken() {
			try {
				const response = await axios.get('/api/auth/refresh', {
					headers: {
						Authorization: `Bearer ${this.userToken}`
					}
				})

				if (response.data.access_token) {
					this.userToken = response.data.access_token
				}
			} catch (error) {
				console.error('Failed to refresh token:', error)
				this.logout()
			}
		},

		logout() {
			this.userToken = null
			this.user = null
			this.isAuthenticated = false
		},

		setLogout() {
			this.logout()
		}
	},

	persist: {
		key: 'customer-portal-auth',
		storage: localStorage,
		paths: ['userToken', 'user', 'isAuthenticated']
	}
})
