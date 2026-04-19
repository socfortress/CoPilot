<template>
	<n-modal
		v-model:show="isOpen"
		preset="card"
		display-directive="show"
		class="w-[90vw]! max-w-133!"
		segmented
		title="Change Password"
	>
		<n-form :disabled="loading">
			<n-form-item path="currentPassword" label="Current Password" required>
				<n-input
					v-model:value="currentPassword"
					type="password"
					size="large"
					show-password-on="click"
					:input-props="{ autocomplete: 'new-password' }"
					placeholder="Enter current password"
				/>
			</n-form-item>
			<n-form-item path="newPassword" label="New Password" required>
				<n-input
					v-model:value="newPassword"
					type="password"
					size="large"
					show-password-on="click"
					:input-props="{ autocomplete: 'new-password' }"
					placeholder="Enter new password"
				/>
			</n-form-item>
			<n-form-item path="confirmPassword" label="Confirm Password" required>
				<n-input
					v-model:value="confirmPassword"
					type="password"
					show-password-on="click"
					placeholder="Enter confirm password"
					:input-props="{ autocomplete: 'new-password' }"
					size="large"
					:disabled="!newPassword"
				>
					<template #prefix>
						<Icon name="carbon:locked" class="text-tertiary! mr-1" />
					</template>
				</n-input>
			</n-form-item>
		</n-form>

		<template #footer>
			<div class="flex w-full justify-end gap-4">
				<n-button secondary :disabled="loading" @click="closeModal">Cancel</n-button>
				<n-button type="primary" :loading :disabled="!isValid" @click="handleSubmit()">
					Change Password
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NButton, NForm, NFormItem, NInput, NModal, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const emit = defineEmits<{
	(e: "close"): void
	(e: "success"): void
}>()

const isOpen = defineModel<boolean>("open", { default: false })
const loading = defineModel<boolean>("loading", { default: false })

const message = useMessage()
const currentPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")

const isValid = computed(() => {
	return (
		currentPassword.value.length > 0 && newPassword.value.length >= 8 && newPassword.value === confirmPassword.value
	)
})

function closeModal() {
	if (!loading.value) {
		resetForm()
		isOpen.value = false
		emit("close")
	}
}

function resetForm() {
	currentPassword.value = ""
	newPassword.value = ""
	confirmPassword.value = ""
}

async function handleSubmit() {
	// Validate passwords match
	if (newPassword.value !== confirmPassword.value) {
		message.error("New passwords do not match")
		return
	}

	// Validate password length
	if (newPassword.value.length < 8) {
		message.error("Password must be at least 8 characters long")
		return
	}

	loading.value = true

	try {
		// Get token and username from localStorage
		const token = localStorage.getItem("customer-portal-auth-token")
		const userStr = localStorage.getItem("customer-portal-user")

		if (!token || !userStr) {
			message.error("Authentication required. Please log in again.")
			return
		}

		const user = JSON.parse(userStr)
		const username = user.username

		// Call the reset-password/me endpoint
		const response = await Api.auth.resetPassword(username, newPassword.value)

		if (response.data.success) {
			message.success("Password changed successfully!")
			emit("success")
			closeModal()
		} else {
			message.error(response.data.message || "Failed to change password")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}
</script>
