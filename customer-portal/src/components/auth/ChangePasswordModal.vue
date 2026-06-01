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
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

const emit = defineEmits<{
	(e: "close"): void
	(e: "success"): void
}>()

const isOpen = defineModel<boolean>("open", { default: false })
const loading = defineModel<boolean>("loading", { default: false })

const message = useMessage()
const authStore = useAuthStore()
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

	// Mirror the backend complexity requirements so the user gets a clear message
	// instead of an opaque 422 from the API.
	if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,72}$/.test(newPassword.value)) {
		message.error(
			"Password must be 8-72 characters and include an uppercase letter, a lowercase letter, a number, and a special character (@$!%*?&#)"
		)
		return
	}

	const username = authStore.userName
	if (!username) {
		message.error("Authentication required. Please log in again.")
		return
	}

	loading.value = true

	try {
		// Token is injected by the HTTP client from the auth store.
		const response = await Api.auth.resetPassword(username, newPassword.value, currentPassword.value)

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
