<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Security</h3>
			<p class="text-secondary text-sm">Manage 2FA and passwords for the user accounts scoped to this customer</p>
		</div>

		<n-alert v-if="!smtpConfigured" type="warning" :bordered="false" class="text-xs">
			SMTP is not configured, so sending a temporary password by email is disabled. Set the
			<code>SMTP_*</code>
			variables in the backend environment to enable it. All other actions work.
		</n-alert>

		<n-spin :show="loading">
			<n-table v-if="users.length" bordered :single-line="false" size="small">
				<thead>
					<tr>
						<th>User</th>
						<th>Role</th>
						<th>2FA (TOTP)</th>
						<th>Last login</th>
						<th class="text-right!">Actions</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="user in users" :key="user.id">
						<td>
							<div class="flex flex-col">
								<span class="font-semibold">{{ user.username }}</span>
								<span class="text-secondary text-xs">{{ user.email }}</span>
							</div>
						</td>
						<td>{{ roleLabel(user.role_name) }}</td>
						<td>
							<n-tag :type="user.totp_enabled ? 'success' : 'default'" size="small" round>
								<template #icon>
									<Icon :name="user.totp_enabled ? EnabledIcon : DisabledIcon" :size="13" />
								</template>
								{{ user.totp_enabled ? "Enabled" : "Disabled" }}
							</n-tag>
						</td>
						<td>
							<span class="font-mono text-xs">
								{{ user.last_login_at ? formatDate(user.last_login_at, dFormats.datetime) : "Never" }}
							</span>
						</td>
						<td>
							<div class="flex flex-wrap items-center justify-end gap-2">
								<n-button
									size="tiny"
									secondary
									:disabled="!user.totp_enabled || busyUserId === user.id"
									@click="confirmResetTotp(user)"
								>
									<template #icon><Icon :name="ResetIcon" :size="13" /></template>
									Reset 2FA
								</n-button>

								<n-tooltip :disabled="smtpConfigured" trigger="hover">
									<template #trigger>
										<n-button
											size="tiny"
											secondary
											:disabled="!smtpConfigured || busyUserId === user.id"
											@click="confirmSendTempPassword(user)"
										>
											<template #icon><Icon :name="MailIcon" :size="13" /></template>
											Email temp password
										</n-button>
									</template>
									SMTP is not configured
								</n-tooltip>

								<n-button size="tiny" type="warning" secondary @click="openPasswordModal(user)">
									<template #icon><Icon :name="KeyIcon" :size="13" /></template>
									Set password
								</n-button>
							</div>
						</td>
					</tr>
				</tbody>
			</n-table>

			<n-empty
				v-else
				description="No customer users are scoped to this customer"
				class="min-h-32 justify-center"
			/>
		</n-spin>

		<n-modal
			v-model:show="showPasswordModal"
			preset="card"
			title="Set a new password"
			class="max-w-120!"
			display-directive="show"
			closable
		>
			<n-form ref="pwFormRef" :model="pwForm" :rules="pwRules" label-placement="top">
				<p class="text-secondary mb-3 text-sm">
					Overwrite the password for
					<strong>{{ passwordTarget?.username }}</strong>
					. The user will need to sign in with this new password.
				</p>
				<n-form-item label="New password" path="newPassword">
					<n-input
						v-model:value="pwForm.newPassword"
						type="password"
						show-password-on="click"
						placeholder="At least 8 characters"
					/>
				</n-form-item>
				<n-form-item label="Confirm password" path="confirmPassword">
					<n-input
						v-model:value="pwForm.confirmPassword"
						type="password"
						show-password-on="click"
						placeholder="Repeat the password"
					/>
				</n-form-item>
				<div class="mt-4 flex justify-end gap-3">
					<n-button @click="showPasswordModal = false">Cancel</n-button>
					<n-button type="warning" :loading="savingPassword" @click="submitPassword">Set password</n-button>
				</div>
			</n-form>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { CustomerSecurityUser } from "@/types/security"
import {
	NAlert,
	NButton,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NModal,
	NSpin,
	NTable,
	NTag,
	NTooltip,
	useDialog,
	useMessage
} from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const EnabledIcon = "carbon:security"
const DisabledIcon = "carbon:unlocked"
const ResetIcon = "carbon:reset"
const MailIcon = "carbon:email"
const KeyIcon = "carbon:password"

const message = useMessage()
const dialog = useDialog()
const dFormats = useSettingsStore().dateFormat

const users = ref<CustomerSecurityUser[]>([])
const loading = ref(false)
const smtpConfigured = ref(true)
const busyUserId = ref<number | null>(null)

const showPasswordModal = ref(false)
const passwordTarget = ref<CustomerSecurityUser | null>(null)
const savingPassword = ref(false)
const pwFormRef = ref<FormInst | null>(null)
const pwForm = ref({ newPassword: "", confirmPassword: "" })

const pwRules: FormRules = {
	newPassword: [{ required: true, min: 8, message: "At least 8 characters", trigger: ["blur", "input"] }],
	confirmPassword: [
		{
			required: true,
			validator: (_rule, value: string) => {
				if (value !== pwForm.value.newPassword) return new Error("Passwords do not match")
				return true
			},
			trigger: ["blur", "input"]
		}
	]
}

function roleLabel(role?: string | null) {
	const labels: Record<string, string> = {
		admin: "Admin",
		analyst: "Analyst",
		scheduler: "Scheduler",
		customer_user: "Customer"
	}
	return role ? (labels[role] ?? role) : "—"
}

async function loadUsers() {
	loading.value = true
	try {
		const response = await Api.security.listCustomerUsers(customerCode)
		if (response.data.success) {
			users.value = response.data.users
		} else {
			message.error(response.data.message || "Failed to load users")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to load users")
	} finally {
		loading.value = false
	}
}

async function loadSmtpStatus() {
	try {
		const response = await Api.security.getSmtpStatus()
		smtpConfigured.value = response.data.configured
	} catch {
		smtpConfigured.value = false
	}
}

function confirmResetTotp(user: CustomerSecurityUser) {
	dialog.warning({
		title: "Reset 2FA",
		content: `Force-reset two-factor authentication for "${user.username}"? They will be able to sign in with just their password and can re-enrol afterwards.`,
		positiveText: "Reset 2FA",
		negativeText: "Cancel",
		onPositiveClick: async () => {
			busyUserId.value = user.id
			try {
				const response = await Api.security.forceResetTotp(user.id)
				if (response.data.success) {
					message.success(response.data.message || "2FA reset")
					await loadUsers()
				} else {
					message.error(response.data.message || "Failed to reset 2FA")
				}
			} catch (error) {
				message.error(getApiErrorMessage(error as ApiError) || "Failed to reset 2FA")
			} finally {
				busyUserId.value = null
			}
		}
	})
}

function confirmSendTempPassword(user: CustomerSecurityUser) {
	dialog.warning({
		title: "Email a temporary password",
		content: `Generate a temporary password for "${user.username}", set it as their password, and email it to ${user.email}? Their current password will stop working.`,
		positiveText: "Send",
		negativeText: "Cancel",
		onPositiveClick: async () => {
			busyUserId.value = user.id
			try {
				const response = await Api.security.sendTempPassword(user.id)
				if (response.data.success) {
					message.success(response.data.message || "Temporary password sent")
				} else {
					message.error(response.data.message || "Failed to send temporary password")
				}
			} catch (error) {
				message.error(getApiErrorMessage(error as ApiError) || "Failed to send temporary password")
			} finally {
				busyUserId.value = null
			}
		}
	})
}

function openPasswordModal(user: CustomerSecurityUser) {
	passwordTarget.value = user
	pwForm.value = { newPassword: "", confirmPassword: "" }
	showPasswordModal.value = true
}

async function submitPassword() {
	if (!pwFormRef.value || !passwordTarget.value) return
	try {
		await pwFormRef.value.validate()
	} catch {
		return
	}

	savingPassword.value = true
	try {
		const response = await Api.auth.resetPassword(passwordTarget.value.username, pwForm.value.newPassword)
		if (response.data.success) {
			message.success(`Password updated for ${passwordTarget.value.username}`)
			showPasswordModal.value = false
		} else {
			message.error(response.data.message || "Failed to update password")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to update password")
	} finally {
		savingPassword.value = false
	}
}

onBeforeMount(() => {
	loadUsers()
	loadSmtpStatus()
})
</script>
