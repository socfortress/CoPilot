<template>
	<div class="page">
		<n-card class="header flex flex-col" content-class="p-0!">
			<div class="user-info flex flex-wrap">
				<div class="propic">
					<n-avatar :size="100" :src="userPic" round :img-props="{ alt: 'avatar' }" />
					<ImageCropper
						v-if="propicEnabled"
						v-slot="{ openCropper }"
						shape="circle"
						placeholder="Select your profile picture"
						@crop="setCroppedImage"
					>
						<Icon :name="EditIcon" :size="16" class="edit" @click="openCropper()" />
					</ImageCropper>
				</div>
				<div class="info flex grow flex-col justify-center">
					<div class="name">
						<h1>{{ userName }}</h1>
					</div>
					<div class="details flex flex-wrap">
						<div class="item">
							<n-tooltip placement="top">
								<template #trigger>
									<div class="tooltip-wrap">
										<Icon :name="RoleIcon" />
										<span>{{ userRole }}</span>
									</div>
								</template>
								<span>Role</span>
							</n-tooltip>
						</div>
						<div v-if="userEmail" class="item">
							<div class="tooltip-wrap">
								<Icon :name="EmailIcon" />
								<span>{{ userEmail }}</span>
							</div>
						</div>
					</div>
				</div>
				<div class="actions">
					<ChangePassword :user="{ username: userName, id: 0, email: '' }" size="small" />

					<ImageCropper
						v-if="propicEnabled"
						v-slot="{ openCropper }"
						shape="circle"
						placeholder="Select your profile picture"
						@crop="setCroppedImage"
					>
						<n-button size="large" type="primary" @click="openCropper()">Edit profile image</n-button>
					</ImageCropper>
				</div>
			</div>
			<div class="section-selector">
				<n-tabs v-model:value="tabActive">
					<n-tab name="settings">Settings</n-tab>
					<n-tab name="security">Security</n-tab>
				</n-tabs>
			</div>
		</n-card>
		<div class="main">
			<n-tabs v-model:value="tabActive" tab-class="hidden!" animated>
				<n-tab-pane name="settings">
					<ProfileSettings />
				</n-tab-pane>
				<n-tab-pane name="security">
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
									Add an extra layer of security to your account. You will need an authenticator app
									like Google Authenticator, Authy, or Microsoft Authenticator.
								</p>
								<n-button type="primary" @click="startSetup">
									<template #icon>
										<Icon name="carbon:locked" />
									</template>
									Enable Two-Factor Authentication
								</n-button>
							</div>

							<!-- ── Setup flow: QR + verify ── -->
							<div v-if="setupData && (!twoFaEnabled || setupStep === 3)">
								<n-steps :current="setupStep" size="small" class="mb-6">
									<n-step title="Scan QR code" />
									<n-step title="Verify code" />
									<n-step title="Save backup codes" />
								</n-steps>

								<!-- Step 1: QR -->
								<div v-if="setupStep === 1">
									<p class="mb-4">
										Scan this QR code with your authenticator app:
									</p>
									<div class="mb-4 flex justify-center">
										<img :src="setupData.qr_data_uri" alt="TOTP QR Code" class="rounded border" />
									</div>
									<n-collapse-transition :show="showManualKey">
										<n-alert type="info" class="mb-4" :show-icon="false">
											<strong>Manual entry key:</strong>
											<n-code class="ml-2">{{ setupData.secret }}</n-code>
										</n-alert>
									</n-collapse-transition>
									<n-button text size="small" class="mb-4" @click="showManualKey = !showManualKey">
										{{ showManualKey ? "Hide" : "Show" }} manual entry key
									</n-button>

									<n-alert type="warning" class="mb-4">
										<template #icon>
											<Icon name="carbon:time" />
										</template>
										<strong>Important:</strong> Make sure your device clock is accurate.
										TOTP codes are time-sensitive and allow only a &plusmn;30 second tolerance window.
									</n-alert>

									<div class="flex justify-end">
										<n-button type="primary" @click="setupStep = 2">Next: Verify</n-button>
									</div>
								</div>

								<!-- Step 2: Verify -->
								<div v-if="setupStep === 2">
									<p class="mb-4">
										Enter the 6-digit code from your authenticator app to confirm:
									</p>
									<n-input
										v-model:value="verifyCode"
										placeholder="123456"
										maxlength="6"
										class="max-w-50 mb-4"
										size="large"
										@keydown.enter="confirmSetup"
									/>
									<div class="flex justify-end gap-2">
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
								<div v-if="setupStep === 3">
									<n-alert type="success" class="mb-4">
										<template #icon>
											<Icon name="carbon:checkmark-filled" />
										</template>
										Two-factor authentication is now enabled!
									</n-alert>
									<p class="mb-2 font-semibold">
										Save these backup codes — they are shown only once:
									</p>
									<div class="backup-codes-grid mb-4">
										<n-code v-for="c in setupData.backup_codes" :key="c" class="backup-code">
											{{ c }}
										</n-code>
									</div>
									<div class="flex gap-2">
										<n-button @click="copyBackupCodes(setupData!.backup_codes)">
											<template #icon>
												<Icon name="carbon:copy" />
											</template>
											Copy all
										</n-button>
										<n-button @click="downloadBackupCodes(setupData!.backup_codes)">
											<template #icon>
												<Icon name="carbon:download" />
											</template>
											Download .txt
										</n-button>
										<n-button type="primary" class="ml-auto!" @click="finishSetup">Done</n-button>
									</div>
								</div>
							</div>

							<!-- ── 2FA enabled — show disable + regenerate ── -->
							<div v-if="twoFaEnabled">
								<p class="text-secondary mb-4">
									Two-factor authentication is active. You will be asked for a code from your
									authenticator app every time you log in.
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
					<n-modal v-model:show="showRegenModal" preset="card" title="Regenerate Backup Codes" :style="{ maxWidth: '500px' }">
						<div v-if="!regenCodes">
							<p class="mb-4">Enter your TOTP code to generate new backup codes. Old codes will be invalidated.</p>
							<n-input
								v-model:value="regenCode"
								placeholder="6-digit code"
								maxlength="6"
								class="mb-4"
								@keydown.enter="regenBackupCodes"
							/>
							<div class="flex justify-end gap-2">
								<n-button @click="showRegenModal = false">Cancel</n-button>
								<n-button type="primary" :loading="regenerating" :disabled="regenCode.length < 6" @click="regenBackupCodes">
									Regenerate
								</n-button>
							</div>
						</div>
						<div v-else>
							<n-alert type="success" class="mb-4">
								New backup codes generated. Save them — they are shown only once.
							</n-alert>
							<div class="backup-codes-grid mb-4">
								<n-code v-for="c in regenCodes" :key="c" class="backup-code">{{ c }}</n-code>
							</div>
							<div class="flex gap-2">
								<n-button @click="copyBackupCodes(regenCodes!)">
									<template #icon><Icon name="carbon:copy" /></template>
									Copy all
								</n-button>
								<n-button @click="downloadBackupCodes(regenCodes!)">
									<template #icon><Icon name="carbon:download" /></template>
									Download .txt
								</n-button>
								<n-button type="primary" class="ml-auto!" @click="closeRegenModal">Done</n-button>
							</div>
						</div>
					</n-modal>
				</n-tab-pane>
			</n-tabs>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import type { TOTPSetupResponse } from "@/api/endpoints/totp"
import {
	NAlert,
	NAvatar,
	NButton,
	NCard,
	NCode,
	NCollapseTransition,
	NInput,
	NModal,
	NPopconfirm,
	NSpin,
	NStep,
	NSteps,
	NTab,
	NTabPane,
	NTabs,
	NTag,
	NTooltip,
	useMessage
} from "naive-ui"
import { onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import ProfileSettings from "@/components/profile/ProfileSettings.vue"
import ChangePassword from "@/components/users/ChangePassword.vue"
import { useAuthStore } from "@/stores/auth"

const propicEnabled = false

const RoleIcon = "tabler:user"
const EditIcon = "uil:image-edit"
const EmailIcon = "carbon:email"

const tabActive = ref("settings")
const authStore = useAuthStore()
const message = useMessage()

const userRole = authStore.userRoleName
const userName = authStore.userName
const userEmail = authStore.userEmail
const userPic = ref(authStore.userPic)

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	userPic.value = canvas.toDataURL()
}

// ── 2FA state ────────────────────────────────────────────────────────────────
const twoFaLoading = ref(false)
const twoFaEnabled = ref(false)
const setupData = ref<TOTPSetupResponse | null>(null)
const setupStep = ref(1)
const showManualKey = ref(false)
const verifyCode = ref("")
const verifying = ref(false)

const showDisableModal = ref(false)
const disableCode = ref("")
const disabling = ref(false)

const showRegenModal = ref(false)
const regenCode = ref("")
const regenCodes = ref<string[] | null>(null)
const regenerating = ref(false)

async function load2faStatus() {
	twoFaLoading.value = true
	try {
		const res = await Api.totp.getStatus()
		twoFaEnabled.value = res.data.enabled
	} catch {
		// 2FA endpoint might not exist yet — ignore
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
		await Api.totp.verifySetup(verifyCode.value)
		twoFaEnabled.value = true
		setupStep.value = 3
		message.success("Two-factor authentication enabled!")
	} catch (err: any) {
		message.error(err.response?.data?.detail || "Invalid code. Try again.")
	} finally {
		verifying.value = false
	}
}

function finishSetup() {
	setupData.value = null
	setupStep.value = 1
	verifyCode.value = ""
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
		message.error(err.response?.data?.detail || "Failed to disable 2FA")
	} finally {
		disabling.value = false
	}
}

async function regenBackupCodes() {
	regenerating.value = true
	try {
		const res = await Api.totp.regenerateBackupCodes(regenCode.value)
		regenCodes.value = res.data.backup_codes
		regenCode.value = ""
		message.success("Backup codes regenerated")
	} catch (err: any) {
		message.error(err.response?.data?.detail || "Failed to regenerate codes")
	} finally {
		regenerating.value = false
	}
}

function closeRegenModal() {
	showRegenModal.value = false
	regenCodes.value = null
	regenCode.value = ""
}

function copyBackupCodes(codes: string[]) {
	navigator.clipboard.writeText(codes.join("\n"))
	message.success("Backup codes copied to clipboard")
}

function downloadBackupCodes(codes: string[]) {
	const text = "CoPilot — 2FA Backup Codes\n" + "=".repeat(30) + "\n\n" + codes.join("\n") + "\n\nKeep these codes safe. Each code can only be used once.\n"
	const blob = new Blob([text], { type: "text/plain" })
	const url = URL.createObjectURL(blob)
	const a = document.createElement("a")
	a.href = url
	a.download = "copilot-2fa-backup-codes.txt"
	a.click()
	URL.revokeObjectURL(url)
}

onMounted(() => {
	load2faStatus()
})
</script>

<style lang="scss" scoped>
.page {
	.header {
		.user-info {
			gap: 30px;
			padding: 30px;
			padding-bottom: 20px;
			border-block-end: 1px solid var(--border-color);
			container-type: inline-size;

			.propic {
				position: relative;
				height: 100px;

				.edit {
					display: none;
					align-items: center;
					justify-content: center;
					background-color: var(--primary-color);
					color: var(--bg-default-color);
					position: absolute;
					width: 26px;
					height: 26px;
					border-radius: 50%;
					top: -1px;
					right: -1px;
					border: 1px solid var(--bg-default-color);
					cursor: pointer;
				}
			}
			.info {
				.name {
					margin-bottom: 12px;

					@media (max-width: 450px) {
						h1 {
							font-size: 28px;
						}
					}
				}

				.details {
					gap: 24px;

					.item {
						.tooltip-wrap {
							display: flex;
							align-items: center;
							gap: 8px;
							line-height: 1;
						}
					}
				}
			}

			@container (max-width: 900px) {
				.propic {
					.edit {
						display: flex;
					}
				}
			}
		}
		.section-selector {
			padding: 0px 30px;
			padding-top: 15px;

			:deep() {
				.n-tabs .n-tabs-tab {
					padding-bottom: 20px;
				}
			}
		}
	}

	.main {
		margin-top: 18px;
	}
}

.backup-codes-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 8px;

	.backup-code {
		padding: 6px 12px;
		font-size: 14px;
		font-family: monospace;
		letter-spacing: 1px;
	}
}
</style>
