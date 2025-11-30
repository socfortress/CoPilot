<template>
    <div class="flex min-h-screen">
        <!-- Left side - Login Form -->
        <div class="flex flex-1 items-center justify-center bg-gray-50 px-4 sm:px-6 lg:px-8">
            <div class="w-full max-w-md space-y-8">
                <!-- Logo and Title -->
                <div class="text-center">
                    <div class="mb-6 min-h-12">
                        <img
                            v-if="portalLogo && showLogo"
                            class="mx-auto h-12 w-auto"
                            :src="portalLogo"
                            :alt="portalTitle"
                            @error="showLogo = false"
                        />
                    </div>
                    <h2 class="mb-2 min-h-10 text-4xl font-bold text-gray-900">{{ portalTitle }}</h2>
                    <p class="text-lg text-gray-600">Access your security dashboard and reports</p>
                </div>

                <!-- Login Form -->
                <div class="mt-8 rounded-lg bg-white px-6 py-8 shadow-lg">
                    <form @submit.prevent="handleLogin" class="space-y-6">
                        <div v-if="error" class="rounded-md border border-red-200 bg-red-50 p-3">
                            <div class="text-sm text-red-700">{{ error }}</div>
                        </div>

                        <div>
                            <label for="username" class="mb-2 block text-sm font-medium text-gray-700">Username</label>
                            <input
                                id="username"
                                v-model="username"
                                type="text"
                                required
                                autocomplete="username"
                                class="block w-full rounded-md border border-gray-300 px-3 py-3 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                placeholder="Enter your username"
                            />
                        </div>

                        <div>
                            <label for="password" class="mb-2 block text-sm font-medium text-gray-700">Password</label>
                            <input
                                id="password"
                                v-model="password"
                                type="password"
                                required
                                autocomplete="current-password"
                                class="block w-full rounded-md border border-gray-300 px-3 py-3 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                placeholder="Enter your password"
                            />
                        </div>

                        <div>
                            <button
                                type="submit"
                                :disabled="loading || !username || !password"
                                class="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-3 text-base font-medium text-white transition-colors duration-200 hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <span v-if="loading" class="flex items-center">
                                    <svg
                                        class="mr-3 -ml-1 h-5 w-5 animate-spin text-white"
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                    >
                                        <circle
                                            class="opacity-25"
                                            cx="12"
                                            cy="12"
                                            r="10"
                                            stroke="currentColor"
                                            stroke-width="4"
                                        ></circle>
                                        <path
                                            class="opacity-75"
                                            fill="currentColor"
                                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                        ></path>
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
        <div class="relative hidden flex-1 lg:block">
            <div class="absolute inset-0 bg-linear-to-br from-indigo-600 to-purple-700">
                <div class="bg-opacity-20 absolute inset-0 bg-black"></div>
                <div class="relative flex h-full items-center justify-center p-12">
                    <div class="text-center text-white">
                        <h3 class="mb-4 text-3xl font-bold">Welcome to Your Security Dashboard</h3>
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
import { ref, computed } from "vue"
import { useRouter } from "vue-router"
import { usePortalSettingsStore } from "../stores/portalSettings"
import { AuthAPI } from "../api/auth"

const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

const username = ref("")
const password = ref("")
const loading = ref(false)
const error = ref("")
const showLogo = ref(true)

const portalTitle = computed(() => portalSettingsStore.portalTitle)
const portalLogo = computed(() => portalSettingsStore.portalLogo)

const handleLogin = async () => {
    loading.value = true
    error.value = ""

    try {
        const data = await AuthAPI.login({
            username: username.value,
            password: password.value
        })

        if (data.access_token) {
            const decoded = AuthAPI.decodeToken(data.access_token)

            if (!decoded) {
                error.value = "Invalid token received"
                return
            }

            // Check if user has customer_user scope
            if (AuthAPI.hasCustomerAccess(decoded.scopes)) {
                // Store the token and user info
                localStorage.setItem("customer-portal-auth-token", data.access_token)
                localStorage.setItem(
                    "customer-portal-user",
                    JSON.stringify({
                        username: username.value,
                        scopes: decoded.scopes
                    })
                )

                router.push("/")
            } else {
                error.value = "Access denied. Customer portal is for customer users only."
            }
        } else {
            error.value = "Login failed"
        }
    } catch (err: any) {
        console.error("Login error:", err)

        // Enhanced error message extraction - prioritize message over detail
        if (err.response?.data?.message) {
            error.value = err.response.data.message
        } else if (err.response?.data?.detail) {
            error.value = err.response.data.detail
        } else if (err.message) {
            error.value = err.message
        } else {
            error.value = "Network error. Please try again."
        }
    } finally {
        loading.value = false
    }
}
</script>
