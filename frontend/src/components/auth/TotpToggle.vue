<template>
	<div>
		<!-- 2FA Section -->
		<n-card title="Two-Factor Authentication (TOTP)">
			<template #header-extra>
				<n-tag :type="twoFaEnabled ? 'success' : 'default'" size="small">
					{{ twoFaEnabled ? "Enabled" : "Disabled" }}
				</n-tag>
			</template>

			<n-spin :show="twoFaLoading">
				<!-- ── 2FA disabled — show enable button ── -->
				<div v-if="!twoFaEnabled && !setupData">
					<p class="text-secondary mb-4">
						Add an extra layer of security to your account. You will need an authenticator app like Google
						Authenticator, Authy, or Microsoft Authenticator.
					</p>
					<n-button type="primary" @click="startSetup">
						<template #icon>
							<Icon name="carbon:locked" />
						</template>
						Enable Two-Factor Authentication
					</n-button>
				</div>

				<!-- ── Setup flow: QR + verify ── -->
				<div v-if="setupData && (!twoFaEnabled || setupStep === 3)" class="flex flex-col gap-6">
					<n-steps :current="setupStep" size="small">
						<n-step title="Scan QR code" />
						<n-step title="Verify code" />
						<n-step title="Save backup codes" />
					</n-steps>

					<!-- Step 1: QR -->
					<div v-if="setupStep === 1" class="flex flex-col gap-4">
						<p>Scan this QR code with your authenticator app:</p>

						<img :src="setupData.qr_data_uri" alt="TOTP QR Code" class="rounded border" width="200" />

						<div>
							<strong>Manual entry key:</strong>
							<n-code class="ml-2">{{ setupData.secret }}</n-code>
						</div>

						<n-alert type="warning">
							<template #icon>
								<Icon name="carbon:time" />
							</template>
							<strong>Important:</strong>
							Make sure your device clock is accurate. TOTP codes are time-sensitive and allow only a
							&plusmn;30 second tolerance window.
						</n-alert>

						<div class="flex justify-between">
							<n-button @click="finishSetup()">Cancel</n-button>
							<n-button type="primary" @click="setupStep = 2">Next</n-button>
						</div>
					</div>

					<!-- Step 2: Verify -->
					<div v-if="setupStep === 2" class="flex flex-col gap-4">
						<p>Enter the 6-digit code from your authenticator app to confirm:</p>

						<n-input-otp
							v-model:value="verifyCode"
							block
							size="large"
							:input-props="{ autocomplete: 'one-time-code', inputmode: 'numeric' }"
							class="max-w-100"
							@finish="confirmSetup()"
							@keydown.enter="confirmSetup()"
						/>

						<div class="flex justify-between gap-2">
							<n-button @click="setupStep = 1">Back</n-button>
							<n-button
								type="primary"
								:loading="verifying"
								:disabled="verifyCode.length < 6"
								@click="confirmSetup"
							>
								Verify &amp; Enable
							</n-button>
						</div>
					</div>

					<!-- Step 3: Backup codes -->
					<div v-if="setupStep === 3" class="flex flex-col gap-4">
						<n-alert type="success">
							<template #icon>
								<Icon name="carbon:checkmark-filled" />
							</template>
							Two-factor authentication is now enabled!
						</n-alert>

						<BackupCodesPanel :codes="setupData?.backup_codes || []" />

						<n-button type="primary" class="ml-auto!" @click="finishSetup">Done</n-button>
					</div>
				</div>

				<!-- ── 2FA enabled — show disable + regenerate ── -->
				<div v-if="twoFaEnabled && !setupStep" class="flex flex-col gap-4">
					<p class="text-secondary">
						Two-factor authentication is active. You will be asked for a code from your authenticator app
						every time you log in.
					</p>
					<div class="flex flex-wrap gap-3">
						<n-popconfirm @positive-click="showDisableModal = true">
							<template #trigger>
								<n-button type="error">
									<template #icon>
										<Icon name="carbon:unlocked" />
									</template>
									Disable 2FA
								</n-button>
							</template>
							Are you sure you want to disable two-factor authentication?
						</n-popconfirm>
						<n-button @click="showRegenModal = true">
							<template #icon>
								<Icon name="carbon:renew" />
							</template>
							Regenerate backup codes
						</n-button>
					</div>
				</div>
			</n-spin>
		</n-card>

		<!-- Disable 2FA Modal -->
		<n-modal v-model:show="showDisableModal" preset="card" title="Disable 2FA" :style="{ maxWidth: '400px' }">
			<p class="mb-4">Enter your TOTP code or a backup code to disable 2FA:</p>
			<n-input
				v-model:value="disableCode"
				placeholder="6-digit code or backup code"
				class="mb-4"
				@keydown.enter="disableTwoFa"
			/>
			<div class="flex justify-end gap-2">
				<n-button @click="showDisableModal = false">Cancel</n-button>
				<n-button type="error" :loading="disabling" :disabled="!disableCode" @click="disableTwoFa">
					Disable
				</n-button>
			</div>
		</n-modal>

		<!-- Regenerate Backup Codes Modal -->
		<n-modal
			v-model:show="showRegenModal"
			preset="card"
			title="Regenerate Backup Codes"
			:style="{ maxWidth: '500px' }"
		>
			<div v-if="!regenCodes" class="flex flex-col gap-4">
				<p>Enter your TOTP code to generate new backup codes. Old codes will be invalidated.</p>
				<n-input-otp
					v-model:value="regenCode"
					block
					size="large"
					:input-props="{ autocomplete: 'one-time-code', inputmode: 'numeric' }"
					@finish="regenBackupCodes()"
					@keydown.enter="regenBackupCodes()"
				/>
				<div class="flex justify-end gap-2">
					<n-button @click="showRegenModal = false">Cancel</n-button>
					<n-button
						type="primary"
						:loading="regenerating"
						:disabled="regenCode.length < 6"
						@click="regenBackupCodes"
					>
						Regenerate
					</n-button>
				</div>
			</div>
			<div v-else class="flex flex-col gap-4">
				<BackupCodesPanel :codes="regenCodes || []" />
				<n-button type="primary" class="ml-auto!" @click="closeRegenModal">Done</n-button>
			</div>
		</n-modal>
	</div>
</template>

<script lang="ts" setup>
import type { TOTPSetupResponse } from "@/api/endpoints/totp"
import {
	NAlert,
	NButton,
	NCard,
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
import Api from "@/api"
import BackupCodesPanel from "@/components/auth/BackupCodesPanel.vue"
import Icon from "@/components/common/Icon.vue"

const message = useMessage()

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
	} catch (err: any) {
		message.error(err.response?.data?.detail || "Failed to start 2FA setup")
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
		message.success("Two-factor authentication enabled!")
	} catch (err: any) {
		message.error(err.response?.data?.message || err.response?.data?.detail || "Invalid code. Try again.")
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
		message.success("Two-factor authentication disabled")
	} catch (err: any) {
		message.error(err.response?.data?.message || err.response?.data?.detail || "Failed to disable 2FA")
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
		message.success("Backup codes regenerated")
	} catch (err: any) {
		message.error(err.response?.data?.message || err.response?.data?.detail || "Failed to regenerate codes")
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
