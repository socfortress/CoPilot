<template>
	<div class="flex flex-col">
		<div class="min-h-17">
			<div class="mb-2 text-sm">{{ $t("auth.totpForm.title") }}</div>

			<n-collapse-transition :show="!showBackupInput">
				<n-input-otp
					ref="twoFaCodeRef"
					v-model:value="twoFaCode"
					block
					size="large"
					:allow-input="allowDigitsOnly"
					@finish="verify2fa()"
					@keydown.enter="verify2fa()"
				>
					<template #default="{ index, ref: otpRef, ...inputProps }">
						<n-input
							:key="index"
							:ref="asOtpInputRef(otpRef)"
							v-bind="inputProps"
							:input-props="{
								type: 'text',
								inputmode: 'numeric',
								pattern: '[0-9]*',
								autocomplete: 'one-time-code'
							}"
						/>
					</template>
				</n-input-otp>
			</n-collapse-transition>
			<n-collapse-transition :show="showBackupInput">
				<n-input
					v-model:value="backupCode"
					:placeholder="$t('auth.totpForm.backupPlaceholder')"
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
			{{ showBackupInput ? $t("auth.totpForm.useBackupCode") : $t("auth.totpForm.verify") }}
		</n-button>

		<div class="mt-4 flex items-center justify-between gap-2">
			<n-button text size="small" @click="cancel2fa()">{{ $t("auth.totpForm.backToLogin") }}</n-button>
			<n-button text size="small" @click="showBackupInput = !showBackupInput">
				{{ showBackupInput ? $t("auth.totpForm.useAuthenticator") : $t("auth.totpForm.useBackupInstead") }}
			</n-button>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { InputOtpInst } from "naive-ui"
import type { VNodeRef } from "vue"
import type { TOTPValidateRequest } from "@/api/endpoints/totp"
import { NButton, NCollapseTransition, NInput, NInputOtp, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { getSafeRedirect } from "@/utils/auth"

const emit = defineEmits<{
	(e: "cancel"): void
}>()

const twoFaTempToken = defineModel<string>("twoFaTempToken", { default: "" })

// Naive UI types the OTP slot `ref` as `(InputInst) => void`; Vue's VNodeRef also gets `null` on unmount.
function asOtpInputRef(slotRef: unknown) {
	return slotRef as VNodeRef
}

// Restrict the OTP boxes to digits: naive-ui applies `allowInput` to both
// typing and pasting. An empty char must pass through so deletions still work.
function allowDigitsOnly(char: string) {
	return char === "" || /^\d$/.test(char)
}

const router = useRouter()
const route = useRoute()
const message = useMessage()
const { t } = useI18n()
const twoFaCodeRef = ref<InputOtpInst | null>(null)
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

	try {
		await authStore.verify2fa(payload)
		router.replace(getSafeRedirect(route.query.redirect))
	} catch (err) {
		message.error((err as Error)?.message || t("auth.signIn.genericError"))
	} finally {
		twoFaLoading.value = false
	}
}

onMounted(() => {
	twoFaCodeRef.value?.focusOnChar(0)
})
</script>
