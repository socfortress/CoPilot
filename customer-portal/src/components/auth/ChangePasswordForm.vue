<template>
	<n-form :disabled="loading">
		<n-form-item path="currentPassword" :label="currentLabelText" required>
			<n-input
				v-model:value="currentPassword"
				type="password"
				size="large"
				show-password-on="click"
				:input-props="{ autocomplete: 'current-password' }"
				data-testid="change-password-current"
				:placeholder="currentPlaceholderText"
			/>
		</n-form-item>
		<n-form-item path="newPassword" :label="$t('auth.changePassword.newLabel')" required>
			<div class="flex w-full flex-col gap-1.5">
				<n-input
					v-model:value="newPassword"
					type="password"
					size="large"
					show-password-on="click"
					:input-props="{ autocomplete: 'new-password', 'aria-describedby': 'change-password-rules' }"
					data-testid="change-password-new"
					:placeholder="$t('auth.changePassword.newPlaceholder')"
				/>
				<!-- In full: as a placeholder the rules were cut off at the field's width. -->
				<p id="change-password-rules" class="text-tertiary text-xs">{{ passwordRequirements() }}</p>
			</div>
		</n-form-item>
		<n-form-item path="confirmPassword" :label="$t('auth.changePassword.confirmLabel')" required>
			<n-input
				v-model:value="confirmPassword"
				type="password"
				show-password-on="click"
				:placeholder="$t('auth.changePassword.confirmPlaceholder')"
				:input-props="{ autocomplete: 'new-password' }"
				data-testid="change-password-confirm"
				size="large"
				:disabled="!newPassword"
			>
				<template #prefix>
					<Icon name="carbon:locked" class="text-tertiary! mr-1" />
				</template>
			</n-input>
		</n-form-item>

		<div class="flex w-full flex-wrap justify-end gap-4">
			<n-button secondary :disabled="loading" data-testid="change-password-cancel" @click="emit('cancel')">
				{{ cancelLabel ?? $t("common.actions.cancel") }}
			</n-button>
			<n-button
				type="primary"
				:loading
				:disabled="!isValid"
				data-testid="change-password-submit"
				@click="handleSubmit()"
			>
				{{ submitLabel ?? $t("auth.changePassword.title") }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"
import { passwordRequirements, translatedPasswordProblem } from "@/utils/password-policy-messages"

/**
 * The password change, shared by the Profile's modal and the change a password an admin
 * chose forces (#1277): the current password, a new one meeting the API's policy, and its
 * confirmation. Its texts default to the Profile's, in the user's language.
 */
const { currentLabel, currentPlaceholder, submitLabel, cancelLabel } = defineProps<{
	currentLabel?: string
	currentPlaceholder?: string
	submitLabel?: string
	cancelLabel?: string
}>()

const emit = defineEmits<{
	(e: "cancel"): void
	(e: "success"): void
}>()

const loading = defineModel<boolean>("loading", { default: false })

const message = useMessage()
const { t } = useI18n()
const authStore = useAuthStore()
const currentLabelText = computed(() => currentLabel ?? t("auth.changePassword.currentLabel"))
const currentPlaceholderText = computed(() => currentPlaceholder ?? t("auth.changePassword.currentPlaceholder"))
const currentPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")

const isValid = computed(() => {
	return (
		currentPassword.value.length > 0 && newPassword.value.length >= 8 && newPassword.value === confirmPassword.value
	)
})

function reset() {
	currentPassword.value = ""
	newPassword.value = ""
	confirmPassword.value = ""
}

async function handleSubmit() {
	if (!isValid.value || loading.value) return

	// Validate passwords match
	if (newPassword.value !== confirmPassword.value) {
		message.error(t("auth.changePassword.mismatch"))
		return
	}

	// The API's own policy, so the user reads which rule failed instead of an opaque 422. It used to
	// allow only letters, digits and @$!%*?&#, refusing passwords that met every rule it listed (#1265).
	const problem = translatedPasswordProblem(newPassword.value)
	if (problem) {
		message.error(problem)
		return
	}

	// The API refuses it too: a password an admin chose must actually be replaced (#1277).
	if (newPassword.value === currentPassword.value) {
		message.error(t("auth.changePassword.sameAsCurrent"))
		return
	}

	const username = authStore.userName
	if (!username) {
		message.error(t("auth.changePassword.authRequired"))
		return
	}

	loading.value = true

	try {
		// Token is injected by the HTTP client from the auth store.
		const response = await Api.auth.resetPassword(username, newPassword.value, currentPassword.value)

		if (response.data.success) {
			message.success(t("auth.changePassword.success"))
			reset()
			emit("success")
		} else {
			message.error(response.data.message || t("auth.changePassword.failed"))
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

defineExpose({ reset })
</script>
