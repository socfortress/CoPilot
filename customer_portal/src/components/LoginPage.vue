<template>
  <div class="min-h-screen flex">
    <!-- Left side - Login Form -->
    <div class="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div class="max-w-md w-full space-y-8">
        <!-- Logo and Title -->
        <div class="text-center">
          <div class="mb-6">
            <img
              class="mx-auto h-12 w-auto"
              src="/logo.svg"
              alt="SOCFortress Logo"
              @error="$event.target.style.display = 'none'"
            />
          </div>
          <h2 class="text-4xl font-bold text-gray-900 mb-2">
            SOCFortress Customer Portal
          </h2>
          <p class="text-lg text-gray-600">
            Access your security dashboard and reports
          </p>
        </div>

        <!-- Login Form -->
        <div class="mt-8 bg-white py-8 px-6 shadow-lg rounded-lg">
          <form @submit.prevent="handleLogin" class="space-y-6">
            <div v-if="error" class="bg-red-50 border border-red-200 rounded-md p-3">
              <div class="text-sm text-red-700">{{ error }}</div>
            </div>

            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                id="username"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                class="block w-full px-3 py-3 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-base"
                placeholder="Enter your username"
              />
            </div>

            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                v-model="password"
                type="password"
                required
                autocomplete="current-password"
                class="block w-full px-3 py-3 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-base"
                placeholder="Enter your password"
              />
            </div>

            <div>
              <button
                type="submit"
                :disabled="loading || !username || !password"
                class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
              >
                <span v-if="loading" class="flex items-center">
                  <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing in...
                </span>
                <span v-else>Sign in</span>
              </button>
            </div>
          </form>
        </div>

        <!-- Footer -->
        <div class="text-center text-sm text-gray-500">
          <p>For customer users only</p>
        </div>
      </div>
    </div>

    <!-- Right side - Background Image/Color -->
    <div class="hidden lg:block relative flex-1">
      <div class="absolute inset-0 bg-gradient-to-br from-indigo-600 to-purple-700">
        <div class="absolute inset-0 bg-black bg-opacity-20"></div>
        <div class="relative h-full flex items-center justify-center p-12">
          <div class="text-center text-white">
            <h3 class="text-3xl font-bold mb-4">
              Welcome to Your Security Dashboard
            </h3>
            <p class="text-xl opacity-90">
              Monitor alerts, track cases, and stay informed about your organization's security posture.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    // Use FormData to match the backend's OAuth2PasswordRequestForm expectation
    const formData = new FormData()
    formData.append('username', username.value)
    formData.append('password', password.value)

    const response = await fetch('/api/auth/token', {
      method: 'POST',
      body: formData  // Send as FormData, not JSON
    })

    if (response.ok) {
      const data = await response.json() as { access_token: string; token_type: string }

      // Check if user is customer_user by decoding the token
      if (data.access_token) {
        try {
          const payload = JSON.parse(atob(data.access_token.split('.')[1]))
          const userScopes = payload.scopes || []

          // Check if user has customer_user scope
          if (userScopes.includes('customer_user')) {
            // Store the token and user info
            localStorage.setItem('customer-portal-auth-token', data.access_token)
            localStorage.setItem('customer-portal-user', JSON.stringify({
              username: username.value,
              scopes: userScopes
            }))

            router.push('/')
          } else {
            error.value = 'Access denied. Customer portal is for customer users only.'
          }
        } catch (err) {
          error.value = 'Invalid token received'
        }
      } else {
        error.value = 'Login failed'
      }
    } else {
      const errorData = await response.json() as { detail?: string }
      error.value = errorData.detail || 'Login failed'
    }
  } catch (err) {
    error.value = 'Network error. Please try again.'
    console.error('Login error:', err)
  } finally {
    loading.value = false
  }
}
</script>
