<template>
	<div class="flex flex-col">
		<div class="min-h-17">
			<div class="mb-2 text-sm">Two-Factor Authentication</div>

			<n-collapse-transition :show="!showBackupInput">
				<n-input-otp
					v-model:value="twoFaCode"
					block
					size="large"
					:input-props="{ autocomplete: 'one-time-code', inputmode: 'numeric' }"
					@finish="verify2fa()"
					@keydown.enter="verify2fa()"
				/>
			</n-collapse-transition>
			<n-collapse-transition :show="showBackupInput">
				<n-input
					v-model:value="backupCode"
					placeholder="Backup code (e.g. ABCD1234EF)"
					size="large"
					@keydown.enter="verify2fa({ useBackupCode: true })"
				/>
			</n-collapse-transition>
		</div>

		<div class="h-6 w-full"></div>

		<n-button
			type="primary"
			class="w-full!"
			size="large"
			:loading="twoFaLoading"
			:disabled="!isValid"
			@click="verify2fa({ useBackupCode: showBackupInput })"
		>
			{{ showBackupInput ? "Use backup code" : "Verify" }}
		</n-button>

		<div class="mt-4 flex items-center justify-between">
			<n-button text size="small" @click="cancel2fa()">← Back to login</n-button>
			<n-button text size="small" @click="showBackupInput = !showBackupInput">
				{{ showBackupInput ? "Use authenticator code" : "Use a backup code instead" }}
			</n-button>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { TOTPValidateRequest } from "@/api/endpoints/totp"
import { NButton, NCollapseTransition, NInput, NInputOtp, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"

const emit = defineEmits<{
	(e: "cancel"): void
}>()

const twoFaTempToken = defineModel<string>("twoFaTempToken", { default: "" })

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const twoFaCode = ref<string[]>([])
const backupCode = ref("")
const twoFaLoading = ref(false)
const showBackupInput = ref(false)

watch(showBackupInput, () => {
	twoFaCode.value = []
	backupCode.value = ""
})

const isValid = computed(() => {
	if (showBackupInput.value) {
		return !!backupCode.value
	}
	return twoFaCode.value.join("").length === 6
})

function cancel2fa() {
	twoFaTempToken.value = ""
	twoFaCode.value = []
	backupCode.value = ""
	showBackupInput.value = false
	emit("cancel")
}

async function verify2fa(params?: { useBackupCode?: boolean }) {
	twoFaLoading.value = true

	const payload: TOTPValidateRequest = {
		temp_token: twoFaTempToken.value,
		code: params?.useBackupCode ? undefined : twoFaCode.value.join(""),
		backup_code: params?.useBackupCode ? backupCode.value : undefined
	}

	authStore
		.verify2fa(payload)
		.then(() => {
			router.push({ path: "/", replace: true })
		})
		.catch(err => {
			message.error(err?.message || err.response?.data?.detail || "An error occurred. Please try again later.")
		})
		.finally(() => {
			twoFaLoading.value = false
		})
}
</script>
