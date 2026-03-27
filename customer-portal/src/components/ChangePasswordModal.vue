<template>
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <div class="mb-4 flex items-center justify-between">
                <h3 class="text-xl font-bold text-gray-900">Change Password</h3>
                <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <form @submit.prevent="handleSubmit" class="space-y-4">
                <!-- Error/Success Messages -->
                <div v-if="error" class="rounded-md border border-red-200 bg-red-50 p-3">
                    <div class="text-sm text-red-700">{{ error }}</div>
                </div>

                <div v-if="success" class="rounded-md border border-green-200 bg-green-50 p-3">
                    <div class="text-sm text-green-700">{{ success }}</div>
                </div>

                <!-- Current Password -->
                <div>
                    <label for="currentPassword" class="mb-2 block text-sm font-medium text-gray-700">
                        Current Password
                    </label>
                    <input
                        id="currentPassword"
                        v-model="currentPassword"
                        type="password"
                        required
                        autocomplete="current-password"
                        class="block w-full rounded-md border border-gray-300 px-3 py-2 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Enter current password"
                    />
                </div>

                <!-- New Password -->
                <div>
                    <label for="newPassword" class="mb-2 block text-sm font-medium text-gray-700">
                        New Password
                    </label>
                    <input
                        id="newPassword"
                        v-model="newPassword"
                        type="password"
                        required
                        autocomplete="new-password"
                        class="block w-full rounded-md border border-gray-300 px-3 py-2 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Enter new password"
                    />
                </div>

                <!-- Confirm New Password -->
                <div>
                    <label for="confirmPassword" class="mb-2 block text-sm font-medium text-gray-700">
                        Confirm New Password
                    </label>
                    <input
                        id="confirmPassword"
                        v-model="confirmPassword"
                        type="password"
                        required
                        autocomplete="new-password"
                        class="block w-full rounded-md border border-gray-300 px-3 py-2 text-base placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Confirm new password"
                    />
                </div>

                <!-- Buttons -->
                <div class="flex justify-end gap-3 pt-4">
                    <button
                        type="button"
                        @click="closeModal"
                        :disabled="loading"
                        class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        :disabled="loading || !isFormValid"
                        class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        <span v-if="loading" class="flex items-center">
                            <svg
                                class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                            >
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path
                                    class="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                ></path>
                            </svg>
                            Changing...
                        </span>
                        <span v-else>Change Password</span>
                    </button>
                </div>
            </form>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import axios from "axios"

const props = defineProps<{
    isOpen: boolean
}>()

const emit = defineEmits<{
    (e: "close"): void
    (e: "success"): void
}>()

const currentPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")
const loading = ref(false)
const error = ref("")
const success = ref("")

const isFormValid = computed(() => {
    return (
        currentPassword.value.length > 0 &&
        newPassword.value.length >= 8 &&
        newPassword.value === confirmPassword.value
    )
})

const closeModal = () => {
    if (!loading.value) {
        resetForm()
        emit("close")
    }
}

const resetForm = () => {
    currentPassword.value = ""
    newPassword.value = ""
    confirmPassword.value = ""
    error.value = ""
    success.value = ""
}

const handleSubmit = async () => {
    error.value = ""
    success.value = ""

    // Validate passwords match
    if (newPassword.value !== confirmPassword.value) {
        error.value = "New passwords do not match"
        return
    }

    // Validate password length
    if (newPassword.value.length < 8) {
        error.value = "Password must be at least 8 characters long"
        return
    }

    loading.value = true

    try {
        // Get token and username from localStorage
        const token = localStorage.getItem("customer-portal-auth-token")
        const userStr = localStorage.getItem("customer-portal-user")

        if (!token || !userStr) {
            error.value = "Authentication required. Please log in again."
            return
        }

        const user = JSON.parse(userStr)
        const username = user.username

        // Call the reset-password/me endpoint
        const response = await axios.post(
            "/api/auth/reset-password/me",
            {
                username: username,
                new_password: newPassword.value
            },
            {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        )

        if (response.data.success) {
            success.value = "Password changed successfully!"

            // Close modal after 1.5 seconds
            setTimeout(() => {
                emit("success")
                closeModal()
            }, 1500)
        } else {
            error.value = response.data.message || "Failed to change password"
        }
    } catch (err: any) {
        console.error("Change password error:", err)

        if (err.response?.data?.detail) {
            error.value = err.response.data.detail
        } else if (err.response?.data?.message) {
            error.value = err.response.data.message
        } else if (err.message) {
            error.value = err.message
        } else {
            error.value = "Failed to change password. Please try again."
        }
    } finally {
        loading.value = false
    }
}
</script>
