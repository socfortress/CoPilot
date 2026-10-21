<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="text-lg font-bold">Security</h3>
				<p class="text-secondary text-sm">
					Manage 2FA and passwords for the user accounts scoped to this customer. A customer admin manages
					this customer's other portal users from the Customer Portal.
				</p>
			</div>
			<!-- The tab stays mounted: a user who changes their password or signs in meanwhile shows on a refresh (#1277). -->
			<n-button size="small" secondary :loading data-testid="security-refresh" @click="loadUsers()">
				<template #icon><Icon :name="RefreshIcon" :size="14" /></template>
				Refresh
			</n-button>
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
							<div class="flex flex-col items-start gap-0.5">
								<span class="font-semibold">{{ user.username }}</span>
								<span class="text-secondary text-xs">{{ user.email }}</span>
								<!-- An admin chose the password; the portal holds the user on the change (#1277). -->
								<n-tag
									v-if="user.must_change_password"
									type="warning"
									size="tiny"
									:bordered="false"
									title="The password was set by an admin. The user must choose a new one at their next sign-in."
									data-testid="security-must-change-password"
								>
									Password change pending
								</n-tag>
								<!-- Manages this customer's other portal users from the portal (#1296). -->
								<n-tag
									v-if="user.is_customer_admin"
									type="info"
									size="tiny"
									:bordered="false"
									title="Manages this customer's portal users from the Customer Portal."
									data-testid="security-customer-admin"
								>
									Customer admin
								</n-tag>
								<n-tag
									v-if="user.disabled_at"
									type="error"
									size="tiny"
									:bordered="false"
									:title="`Disabled on ${formatDate(user.disabled_at, dFormats.datetime, { tz: true })}: the user cannot sign in.`"
									data-testid="security-disabled"
								>
									Disabled
								</n-tag>
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
											@click="openTempPasswordModal(user)"
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

								<!-- Portal accounts only (#1296): the SOC appoints customer admins and can disable an account. -->
								<template v-if="isPortalUser(user)">
									<n-button
										size="tiny"
										secondary
										:disabled="busyUserId === user.id"
										data-testid="security-toggle-customer-admin"
										@click="confirmCustomerAdmin(user)"
									>
										<template #icon><Icon :name="AdminIcon" :size="13" /></template>
										{{ user.is_customer_admin ? "Remove customer admin" : "Make customer admin" }}
									</n-button>
									<n-button
										size="tiny"
										:type="user.disabled_at ? 'success' : 'error'"
										secondary
										:disabled="busyUserId === user.id"
										data-testid="security-toggle-disabled"
										@click="confirmDisabled(user)"
									>
										<template #icon>
											<Icon :name="user.disabled_at ? EnableIcon : DisableIcon" :size="13" />
										</template>
										{{ user.disabled_at ? "Enable" : "Disable" }}
									</n-button>
								</template>
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
			v-model:show="showTempPasswordModal"
			preset="card"
			title="Email a temporary password"
			class="max-w-200!"
			display-directive="show"
			closable
		>
			<div class="flex flex-col gap-4">
				<n-alert type="warning" :bordered="false" class="text-sm">
					This generates a new password for
					<strong>{{ tempPasswordTarget?.username }}</strong>
					<span>,</span>
					sets it, and emails it to {{ tempPasswordTarget?.email }}. Their current password will stop working.
				</n-alert>

				<div class="flex flex-col gap-1">
					<span class="text-secondary text-xs">Template</span>
					<n-select
						v-model:value="selectedTemplateId"
						:options="templateOptions"
						:loading="loadingTemplates"
						:disabled="sendingTempPassword"
					/>
					<!--
						The resolution rule is stated rather than implied: an admin
						choosing between "Acme — Italiano" and "Default" needs to
						know which one a colleague's send would have used.
					-->
					<span class="text-secondary text-xs">
						<template v-if="!templates.length">
							No temporary-password template exists yet, so CoPilot's built-in plain-text email is sent.
							Create one under
							<strong>Notifications → Message Templates</strong>
							with the
							<strong>Temporary password email</strong>
							trigger.
						</template>
						<template v-else>
							Defaults to the most specific template for this customer. Changing it here applies to this
							send only.
						</template>
					</span>
				</div>

				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between gap-4">
						<span class="text-secondary text-xs">
							Preview — the password shown is a placeholder, nothing has been sent or changed
						</span>
						<n-button size="tiny" secondary :loading="loadingPreview" @click="loadPreview">
							<template #icon><Icon :name="RefreshIcon" :size="13" /></template>
							Refresh
						</n-button>
					</div>

					<n-alert v-if="preview?.error" type="error" :bordered="false" class="text-xs">
						{{ preview.error }}
					</n-alert>
					<template v-else-if="preview">
						<div v-if="preview.subject" class="text-xs">
							<span class="text-secondary uppercase">Subject</span>
							<div class="font-mono">{{ preview.subject }}</div>
						</div>
						<!--
							A sandboxed iframe, not v-html: the body is operator-authored
							and renders in an admin's browser. `sandbox` with no allow-*
							tokens blocks scripts, forms and navigation, which is also a
							truer preview since no mail client runs scripts either.
						-->
						<iframe
							v-if="preview.format === 'html'"
							:srcdoc="preview.body"
							sandbox=""
							title="Email preview"
							class="h-80 w-full rounded border bg-white"
						/>
						<n-input
							v-else
							:value="preview.body"
							type="textarea"
							readonly
							:autosize="{ minRows: 6, maxRows: 18 }"
							class="font-mono text-xs!"
						/>
					</template>
					<n-spin v-else :show="loadingPreview" class="min-h-20" />
				</div>

				<div class="flex justify-end gap-3">
					<n-button :disabled="sendingTempPassword" @click="showTempPasswordModal = false">Cancel</n-button>
					<n-button
						type="warning"
						:loading="sendingTempPassword"
						:disabled="!!preview?.error"
						@click="submitTempPassword"
					>
						Send
					</n-button>
				</div>
			</div>
		</n-modal>

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
					<span>.</span>
					The user will need to sign in with this new password.
				</p>
				<n-form-item label="New password" path="newPassword">
					<n-input
						v-model:value="pwForm.newPassword"
						type="password"
						show-password-on="click"
						:placeholder="PASSWORD_REQUIREMENTS"
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
import type { CustomerSecurityUser, TempPasswordEmailPreview, TempPasswordTemplateOption } from "@/types/security"
import {
	NAlert,
	NButton,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NModal,
	NSelect,
	NSpin,
	NTable,
	NTag,
	NTooltip,
	useDialog,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { PASSWORD_REQUIREMENTS, passwordProblem } from "@/utils/password-policy"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const EnabledIcon = "carbon:security"
const DisabledIcon = "carbon:unlocked"
const ResetIcon = "carbon:reset"
const MailIcon = "carbon:email"
const RefreshIcon = "carbon:renew"
const KeyIcon = "carbon:password"
const AdminIcon = "carbon:user-admin"
const DisableIcon = "carbon:user-follow"
const EnableIcon = "carbon:checkmark-outline"

const message = useMessage()
const dialog = useDialog()
const dFormats = useSettingsStore().dateFormat

const users = ref<CustomerSecurityUser[]>([])
const loading = ref(false)
const smtpConfigured = ref(true)
const busyUserId = ref<number | null>(null)

const showTempPasswordModal = ref(false)
const tempPasswordTarget = ref<CustomerSecurityUser | null>(null)
const templates = ref<TempPasswordTemplateOption[]>([])
// NO_TEMPLATE is a real selection, not "nothing picked": it sends CoPilot's
// built-in plain-text body, and it is the only option when a deployment has
// authored none. A sentinel rather than null because Naive's select rejects a
// null option value; template ids are positive autoincrement so 0 is free.
const NO_TEMPLATE = 0
const selectedTemplateId = ref<number>(NO_TEMPLATE)
const preview = ref<TempPasswordEmailPreview | null>(null)
const loadingTemplates = ref(false)
const loadingPreview = ref(false)
const sendingTempPassword = ref(false)

/** The sentinel back to what the API expects. */
function templateIdForApi(): number | null {
	return selectedTemplateId.value === NO_TEMPLATE ? null : selectedTemplateId.value
}

const templateOptions = computed(() => [
	...templates.value.map(t => ({
		label: t.customer_code
			? `${t.name} — ${t.customer_code}`
			: t.is_default
				? `${t.name} (built-in)`
				: `${t.name} (shared)`,
		value: t.id
	})),
	{ label: "No template — CoPilot's built-in plain-text email", value: NO_TEMPLATE }
])

const showPasswordModal = ref(false)
const passwordTarget = ref<CustomerSecurityUser | null>(null)
const savingPassword = ref(false)
const pwFormRef = ref<FormInst | null>(null)
const pwForm = ref({ newPassword: "", confirmPassword: "" })

const pwRules: FormRules = {
	newPassword: [
		{ required: true, message: "New password is required", trigger: ["blur", "input"] },
		{
			// The API's own policy (#1265), so the form never accepts what the API refuses.
			validator: (_rule, value: string) => {
				const problem = passwordProblem(value || "")
				return problem ? new Error(problem) : true
			},
			trigger: ["blur", "input"]
		}
	],
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
		responder: "Responder",
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

function isPortalUser(user: CustomerSecurityUser) {
	return user.role_name === "customer_user"
}

/** Run one action on one user: busy while it runs, the list read again after. */
async function act(user: CustomerSecurityUser, run: () => Promise<{ data: { success: boolean; message?: string } }>) {
	busyUserId.value = user.id
	try {
		const response = await run()
		if (response.data.success) message.success(response.data.message || "Done")
		else message.error(response.data.message || "The action failed")
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "The action failed")
	} finally {
		busyUserId.value = null
		await loadUsers()
	}
}

function confirmCustomerAdmin(user: CustomerSecurityUser) {
	const appoint = !user.is_customer_admin
	dialog.warning({
		title: appoint ? "Make customer admin" : "Remove customer admin",
		content: appoint
			? `Let "${user.username}" manage this customer's portal users from the Customer Portal: invite colleagues, disable and enable them, reset their 2FA and issue temporary passwords?`
			: `"${user.username}" will no longer manage this customer's portal users.`,
		positiveText: appoint ? "Make customer admin" : "Remove",
		negativeText: "Cancel",
		onPositiveClick: () => {
			act(user, () => Api.security.setCustomerAdmin(customerCode, user.id, appoint))
		}
	})
}

function confirmDisabled(user: CustomerSecurityUser) {
	if (user.disabled_at) {
		act(user, () => Api.security.enableUser(user.id))
		return
	}
	dialog.error({
		title: "Disable account",
		content: `Disable "${user.username}"? They will not be able to sign in, and a session they hold ends at its next request. You can enable the account again.`,
		positiveText: "Disable",
		negativeText: "Cancel",
		onPositiveClick: () => {
			act(user, () => Api.security.disableUser(user.id))
		}
	})
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

// Issuing a temporary password used to be a bare confirm dialog. Since the body
// is now operator-authored (#999), the admin has to be able to see WHICH
// template will be used and what it renders to before rotating someone's
// credentials — a wrong-language or half-written template is only visible here.
function openTempPasswordModal(user: CustomerSecurityUser) {
	tempPasswordTarget.value = user
	templates.value = []
	selectedTemplateId.value = NO_TEMPLATE
	preview.value = null
	showTempPasswordModal.value = true
	loadTemplateOptions()
}

async function loadTemplateOptions() {
	const user = tempPasswordTarget.value
	if (!user) return

	loadingTemplates.value = true
	try {
		const response = await Api.security.getTempPasswordEmailOptions({
			userId: user.id,
			customerCode
		})
		templates.value = response.data.templates ?? []
		// The backend's resolution order and the picker's order are the same, so
		// preselecting the resolved id can never disagree with the list's first
		// entry — the admin never has to reconcile two different "defaults".
		selectedTemplateId.value = response.data.resolved_template_id ?? NO_TEMPLATE
	} catch (error) {
		templates.value = []
		selectedTemplateId.value = NO_TEMPLATE
		message.error(getApiErrorMessage(error as ApiError) || "Failed to load email templates")
	} finally {
		loadingTemplates.value = false
	}
	await loadPreview()
}

async function loadPreview() {
	const user = tempPasswordTarget.value
	if (!user) return

	loadingPreview.value = true
	try {
		const response = await Api.security.previewTempPasswordEmail(user.id, {
			template_id: templateIdForApi(),
			customer_code: customerCode
		})
		preview.value = {
			subject: response.data.subject,
			body: response.data.body,
			format: response.data.format,
			error: response.data.error
		}
	} catch (error) {
		preview.value = {
			subject: null,
			body: "",
			format: "text",
			error: getApiErrorMessage(error as ApiError) || "Could not render a preview."
		}
	} finally {
		loadingPreview.value = false
	}
}

// Not debounced: this fires on a dropdown selection, not on typing.
watch(selectedTemplateId, () => {
	if (showTempPasswordModal.value) loadPreview()
})

async function submitTempPassword() {
	const user = tempPasswordTarget.value
	if (!user) return

	sendingTempPassword.value = true
	busyUserId.value = user.id
	try {
		const response = await Api.security.sendTempPassword(user.id, {
			template_id: templateIdForApi(),
			customer_code: customerCode
		})
		if (response.data.success) {
			message.success(
				`${response.data.message || "Temporary password sent"}. ${user.username} will choose a new one at their next sign-in.`
			)
			showTempPasswordModal.value = false
		} else {
			message.error(response.data.message || "Failed to send temporary password")
		}
	} catch (error) {
		// Covers both the 400 "template failed to render, nothing was sent" and
		// the 502 "password was rotated but delivery failed" — the difference
		// matters enormously to the admin, so the server's wording is shown
		// rather than a generic one.
		message.error(getApiErrorMessage(error as ApiError) || "Failed to send temporary password")
	} finally {
		sendingTempPassword.value = false
		busyUserId.value = null
		// Even a failed delivery may have rotated the password: show who must now change it (#1277).
		loadUsers()
	}
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
			message.success(
				`Password updated for ${passwordTarget.value.username}. They will choose a new one at their next sign-in.`
			)
			showPasswordModal.value = false
			loadUsers()
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
