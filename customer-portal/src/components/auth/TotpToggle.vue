<template>
	<div>
		<!-- 2FA Section -->
		<n-card :title="$t('auth.totp.title')">
			<template #header-extra>
				<n-tag :type="twoFaEnabled ? 'success' : 'default'" size="small">
					{{ twoFaEnabled ? $t("auth.totp.enabled") : $t("auth.totp.disabled") }}
				</n-tag>
			</template>

			<n-spin :show="twoFaLoading">
				<!-- ── 2FA disabled — show enable button ── -->
				<div v-if="!twoFaEnabled && !setupData">
					<p class="text-secondary mb-4">
						{{ $t("auth.totp.intro") }}
					</p>
					<n-button type="primary" @click="startSetup">
						<template #icon>
							<Icon name="carbon:locked" />
						</template>
						{{ $t("auth.totp.enable") }}
					</n-button>
				</div>

				<!-- ── Setup flow: QR + verify ── -->
				<div v-if="setupData && (!twoFaEnabled || setupStep === 3)" class="flex flex-col gap-6">
					<n-steps :current="setupStep" size="small">
						<n-step :title="$t('auth.totp.steps.scan')" />
						<n-step :title="$t('auth.totp.steps.verify')" />
						<n-step :title="$t('auth.totp.steps.backup')" />
					</n-steps>

					<!-- Step 1: QR -->
					<div v-if="setupStep === 1" class="flex flex-col gap-4">
						<p>{{ $t("auth.totp.scanPrompt") }}</p>

						<img :src="setupData.qr_data_uri" :alt="$t('auth.totp.qrAlt')" class="rounded border" width="200" />

						<div>
							<strong>{{ $t("auth.totp.manualKey") }}</strong>
							<n-code class="ml-2">{{ setupData.secret }}</n-code>
						</div>

						<n-alert type="warning">
							<template #icon>
								<Icon name="carbon:time" />
							</template>
							<strong>{{ $t("auth.totp.important") }}</strong>
							{{ $t("auth.totp.clockWarning") }}
						</n-alert>

						<div class="flex justify-between">
							<n-button @click="finishSetup()">{{ $t("common.actions.cancel") }}</n-button>
							<n-button type="primary" @click="setupStep = 2">{{ $t("common.actions.next") }}</n-button>
						</div>
					</div>

					<!-- Step 2: Verify -->
					<div v-if="setupStep === 2" class="flex flex-col gap-4">
						<p>{{ $t("auth.totp.verifyPrompt") }}</p>

						<n-input-otp
							v-model:value="verifyCode"
							block
							size="large"
							:allow-input="allowDigitsOnly"
							class="max-w-100"
							@finish="confirmSetup()"
							@keydown.enter="confirmSetup()"
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

						<div class="flex justify-between gap-2">
							<n-button @click="setupStep = 1">{{ $t("common.actions.back") }}</n-button>
							<n-button
								type="primary"
								:loading="verifying"
								:disabled="verifyCode.length < 6"
								@click="confirmSetup"
							>
								{{ $t("auth.totp.verifyAndEnable") }}
							</n-button>
						</div>
					</div>

					<!-- Step 3: Backup codes -->
					<div v-if="setupStep === 3" class="flex flex-col gap-4">
						<n-alert type="success">
							<template #icon>
								<Icon name="carbon:checkmark-filled" />
							</template>
							{{ $t("auth.totp.nowEnabled") }}
						</n-alert>

						<BackupCodesPanel :codes="setupData?.backup_codes || []" />

						<n-button type="primary" class="ml-auto!" @click="finishSetup">{{ $t("auth.totp.done") }}</n-button>
					</div>
				</div>

				<!-- ── 2FA enabled — show disable + regenerate ── -->
				<div v-if="twoFaEnabled && !setupStep" class="flex flex-col gap-4">
					<p class="text-secondary">
						{{ $t("auth.totp.active") }}
					</p>
					<div class="flex flex-wrap gap-3">
						<n-popconfirm @positive-click="showDisableModal = true">
							<template #trigger>
								<n-button type="error">
									<template #icon>
										<Icon name="carbon:unlocked" />
									</template>
									{{ $t("auth.totp.disable2fa") }}
								</n-button>
							</template>
							{{ $t("auth.totp.disableConfirm") }}
						</n-popconfirm>
						<n-button @click="showRegenModal = true">
							<template #icon>
								<Icon name="carbon:renew" />
							</template>
							{{ $t("auth.totp.regenerateCodes") }}
						</n-button>
					</div>
				</div>
			</n-spin>
		</n-card>

		<!-- Disable 2FA Modal -->
		<n-modal v-model:show="showDisableModal" preset="card" :title="$t('auth.totp.disable2fa')" :style="{ maxWidth: '400px' }">
			<p class="mb-4">{{ $t("auth.totp.disablePrompt") }}</p>
			<n-input
				v-model:value="disableCode"
				:placeholder="$t('auth.totp.disablePlaceholder')"
				class="mb-4"
				@keydown.enter="disableTwoFa"
			/>
			<div class="flex justify-end gap-2">
				<n-button @click="showDisableModal = false">{{ $t("common.actions.cancel") }}</n-button>
				<n-button type="error" :loading="disabling" :disabled="!disableCode" @click="disableTwoFa">
					{{ $t("auth.totp.disable") }}
				</n-button>
			</div>
		</n-modal>

		<!-- Regenerate Backup Codes Modal -->
		<n-modal
			v-model:show="showRegenModal"
			preset="card"
			:title="$t('auth.totp.regenerateTitle')"
			:style="{ maxWidth: '500px' }"
		>
			<div v-if="!regenCodes" class="flex flex-col gap-4">
				<p>{{ $t("auth.totp.regeneratePrompt") }}</p>
				<n-input-otp
					v-model:value="regenCode"
					block
					size="large"
					:allow-input="allowDigitsOnly"
					@finish="regenBackupCodes()"
					@keydown.enter="regenBackupCodes()"
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
				<div class="flex justify-end gap-2">
					<n-button @click="showRegenModal = false">{{ $t("common.actions.cancel") }}</n-button>
					<n-button
						type="primary"
						:loading="regenerating"
						:disabled="regenCode.length < 6"
						@click="regenBackupCodes"
					>
						{{ $t("auth.totp.regenerate") }}
					</n-button>
				</div>
			</div>
			<div v-else class="flex flex-col gap-4">
				<BackupCodesPanel :codes="regenCodes || []" />
				<n-button type="primary" class="ml-auto!" @click="closeRegenModal">{{ $t("auth.totp.done") }}</n-button>
			</div>
		</n-modal>
	</div>
</template>

<script lang="ts" setup>
import type { VNodeRef } from "vue"
import type { TOTPSetupResponse } from "@/api/endpoints/totp"
import type { ApiError } from "@/types/common"
import {
	NAlert,
	NButton,
	NCard,
	NCode,
	NInput,
	NInputOtp,
	NModal,
	NPopconfirm,
	NSpin,
	NStep,
	NSteps,
	NTag,
	useMessage
} from "naive-ui"
import { onBeforeMount, ref } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import BackupCodesPanel from "@/components/auth/BackupCodesPanel.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

// Naive UI types the OTP slot `ref` as `(InputInst) => void`; Vue's VNodeRef also gets `null` on unmount.
function asOtpInputRef(slotRef: unknown) {
	return slotRef as VNodeRef
}

// Restrict the OTP boxes to digits: naive-ui applies `allowInput` to both
// typing and pasting. An empty char must pass through so deletions still work.
function allowDigitsOnly(char: string) {
	return char === "" || /^\d$/.test(char)
}

const message = useMessage()
const { t } = useI18n()

// ── 2FA state ────────────────────────────────────────────────────────────────
const twoFaLoading = ref(false)
const twoFaEnabled = ref(false)
const setupData = ref<TOTPSetupResponse | null>(null)
const setupStep = ref(0)
const verifyCode = ref<string[]>([])
const verifying = ref(false)

const showDisableModal = ref(false)
const disableCode = ref("")
const disabling = ref(false)

const showRegenModal = ref(false)
const regenCode = ref<string[]>([])
const regenCodes = ref<string[] | null>(null)
const regenerating = ref(false)

async function load2faStatus() {
	twoFaLoading.value = true

	try {
		const res = await Api.totp.getStatus()
		twoFaEnabled.value = res.data.enabled
	} finally {
		twoFaLoading.value = false
	}
}

async function startSetup() {
	twoFaLoading.value = true

	try {
		const res = await Api.totp.setup()
		setupData.value = res.data
		setupStep.value = 1
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("auth.totp.setupFailed"))
	} finally {
		twoFaLoading.value = false
	}
}

async function confirmSetup() {
	verifying.value = true

	try {
		await Api.totp.verifySetup(verifyCode.value.join(""))
		twoFaEnabled.value = true
		setupStep.value = 3
		message.success(t("auth.totp.enabledToast"))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("auth.totp.invalidCode"))
	} finally {
		verifying.value = false
	}
}

function finishSetup() {
	setupData.value = null
	setupStep.value = 0
	verifyCode.value = []
}

async function disableTwoFa() {
	disabling.value = true
	const isBackup = disableCode.value.length > 6

	try {
		await Api.totp.disable(isBackup ? { backup_code: disableCode.value } : { code: disableCode.value })
		twoFaEnabled.value = false
		showDisableModal.value = false
		disableCode.value = ""
		message.success(t("auth.totp.disabledToast"))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("auth.totp.disableFailed"))
	} finally {
		disabling.value = false
	}
}

async function regenBackupCodes() {
	regenerating.value = true

	try {
		const res = await Api.totp.regenerateBackupCodes(regenCode.value.join(""))
		regenCodes.value = res.data.backup_codes
		regenCode.value = []
		message.success(t("auth.totp.regeneratedToast"))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("auth.totp.regenerateFailed"))
	} finally {
		regenerating.value = false
	}
}

function closeRegenModal() {
	showRegenModal.value = false
	regenCodes.value = null
	regenCode.value = []
}

onBeforeMount(() => {
	load2faStatus()
})
</script>
