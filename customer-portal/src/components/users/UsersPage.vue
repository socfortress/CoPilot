<template>
	<div class="flex flex-col gap-6" data-testid="users-page">
		<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<div class="flex min-w-0 flex-col gap-1.5">
				<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight text-balance">Users</h1>
				<p class="text-secondary max-w-prose text-sm">
					Who can sign in to this portal for your organization. Invite colleagues, disable those who left, and
					help those who lost their authenticator or their password.
				</p>
			</div>
			<n-button
				v-if="data"
				type="primary"
				:disabled="!data.customers.length"
				data-testid="users-invite"
				@click="inviteOpen = true"
			>
				<template #icon><Icon name="carbon:user-follow" :size="16" /></template>
				Invite a user
			</n-button>
		</header>

		<div
			v-if="forbidden"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="users-forbidden"
		>
			<Icon name="carbon:user-admin" :size="28" class="text-tertiary" />
			<p class="text-default font-semibold">Only a customer administrator can manage users</p>
			<p class="text-secondary max-w-md text-sm">
				Your SOC decides who administers your organization's users. Ask your SOC contact if you need to be one.
			</p>
		</div>

		<PanelError
			v-else-if="error && !data"
			:message="error"
			class="bg-default border-default rounded-lg border"
			@retry="load()"
		/>

		<section
			v-else
			class="border-default bg-default @container overflow-hidden rounded-lg border"
			:aria-busy="loading || undefined"
		>
			<div v-if="!data" class="flex flex-col gap-3 p-3" data-testid="users-loading">
				<n-skeleton v-for="n of 4" :key="n" :height="56" :sharp="false" class="rounded-md" />
			</div>
			<ul
				v-else
				class="divide-border m-0 flex list-none flex-col divide-y p-0"
				:class="{ 'opacity-60': loading }"
			>
				<li
					v-for="user of users"
					:key="user.id"
					class="flex flex-col gap-3 px-4 py-3 @2xl:flex-row @2xl:items-center"
					:class="{ 'bg-secondary/40': user.disabled }"
					:data-user="user.username"
					data-testid="users-row"
				>
					<div class="flex min-w-0 grow flex-col gap-1">
						<div class="flex min-w-0 flex-wrap items-center gap-2">
							<span
								class="text-default truncate text-sm font-medium"
								:class="{ 'text-tertiary!': user.disabled }"
							>
								<bdi>{{ user.username }}</bdi>
							</span>
							<n-tag
								v-for="tag of statusTags(user)"
								:key="tag.key"
								:type="tag.type"
								size="tiny"
								:bordered="false"
								:title="tag.title"
								:data-testid="`users-tag-${tag.key}`"
							>
								{{ tag.label }}
							</n-tag>
						</div>
						<span class="text-secondary truncate text-xs">
							<bdi>{{ user.email }}</bdi>
						</span>
						<span class="text-tertiary flex flex-wrap gap-x-3 font-mono text-xs">
							<span v-if="data.customers.length > 1" data-testid="users-customers">
								<bdi>{{ user.customers.map(c => c.customer_name).join(", ") }}</bdi>
							</span>
							<span>2FA {{ user.totp_enabled ? "on" : "off" }}</span>
							<span>
								{{
									user.last_login_at
										? `Last sign-in ${formatDate(user.last_login_at, dFormats.datetime, { tz: true })}`
										: "Never signed in"
								}}
							</span>
						</span>
					</div>

					<div v-if="user.can_manage" class="flex shrink-0 flex-wrap gap-2" data-testid="users-actions">
						<n-button
							size="small"
							secondary
							:disabled="busy === user.id || !user.totp_enabled"
							:title="user.totp_enabled ? undefined : 'Two-factor authentication is not on'"
							data-testid="users-reset-totp"
							@click="confirmResetTotp(user)"
						>
							Reset 2FA
						</n-button>
						<n-button
							size="small"
							secondary
							:disabled="busy === user.id || user.disabled"
							data-testid="users-temporary-password"
							@click="confirmTemporaryPassword(user)"
						>
							Temporary password
						</n-button>
						<n-button
							size="small"
							:type="user.disabled ? 'success' : 'error'"
							secondary
							:loading="busy === user.id"
							data-testid="users-toggle-disabled"
							@click="toggleDisabled(user)"
						>
							{{ user.disabled ? "Enable" : "Disable" }}
						</n-button>
					</div>
					<!-- Why not, rather than buttons that would only be refused. -->
					<span
						v-else
						class="text-tertiary flex shrink-0 items-center gap-1.5 text-xs @2xl:max-w-64"
						data-testid="users-managed-elsewhere"
					>
						<Icon name="carbon:locked" :size="14" class="shrink-0" />
						{{ user.managed_by_soc_reason }}
					</span>
				</li>
			</ul>
		</section>

		<InviteUserDialog
			v-if="data"
			v-model:show="inviteOpen"
			:customers="data.customers"
			:smtp-configured="data.smtp_configured"
			@invited="onInvited"
		/>
		<TemporaryPasswordDialog
			v-model:show="passwordOpen"
			:username="passwordFor?.username ?? ''"
			:email="passwordFor?.email ?? ''"
			:delivery="passwordDelivery"
			:invited="passwordForInvite"
		/>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { TemporaryPasswordDelivery, TenantUser, TenantUsers } from "@/types/users"
import { NButton, NSkeleton, NTag, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import PanelError from "@/components/overview/shared/PanelError.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import InviteUserDialog from "./InviteUserDialog.vue"
import TemporaryPasswordDialog from "./TemporaryPasswordDialog.vue"
import { sortUsers, statusTags } from "./users"

/**
 * A customer admin's Users page (#1296): their customers' portal users, invited, disabled and
 * enabled, helped with their 2FA or a temporary password. Who may be managed is the API's call
 * (`can_manage`); the page shows why not instead of offering what would be refused.
 */

const message = useMessage()
const dialog = useDialog()
const dFormats = useSettingsStore().dateFormat

const data = ref<TenantUsers | null>(null)
const error = ref<string | null>(null)
const forbidden = ref(false)
const busy = ref<number | null>(null)
const { loading, run } = useLatestRequest()

const users = computed(() => sortUsers(data.value?.users ?? []))

const inviteOpen = ref(false)
const passwordOpen = ref(false)
const passwordFor = ref<TenantUser | null>(null)
const passwordDelivery = ref<TemporaryPasswordDelivery | null>(null)
const passwordForInvite = ref(false)

// The password is held only while its dialog is open.
watch(passwordOpen, open => {
	if (!open) passwordDelivery.value = null
})

function load() {
	error.value = null
	return run(
		async signal => {
			const response = await Api.users.list(signal)
			if (signal.aborted) return
			data.value = response.data
			forbidden.value = false
		},
		err => {
			const status = (err as ApiError).response?.status
			if (status === 403) forbidden.value = true
			else error.value = getApiErrorMessage(err as ApiError) || "Could not load the users."
		}
	)
}

/** Put an updated user back in the list. */
function replace(user: TenantUser) {
	if (!data.value) return
	const index = data.value.users.findIndex(u => u.id === user.id)
	if (index >= 0) data.value.users.splice(index, 1, user)
	else data.value.users.push(user)
}

async function act(user: TenantUser, action: () => Promise<{ data: { user: TenantUser; message?: string } }>) {
	busy.value = user.id
	try {
		const response = await action()
		replace(response.data.user)
		message.success(response.data.message || "Done")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "The action failed.")
		await load()
	} finally {
		busy.value = null
	}
}

function toggleDisabled(user: TenantUser) {
	if (user.disabled) {
		act(user, () => Api.users.enable(user.id))
		return
	}
	dialog.warning({
		title: `Disable ${user.username}?`,
		content: "They will not be able to sign in, and a session they have open ends. You can enable them again.",
		positiveText: "Disable",
		negativeText: "Cancel",
		onPositiveClick: () => {
			act(user, () => Api.users.disable(user.id))
		}
	})
}

function confirmResetTotp(user: TenantUser) {
	dialog.warning({
		title: `Reset 2FA for ${user.username}?`,
		content:
			"They sign in with their password alone, and can set up two-factor authentication again from their Profile.",
		positiveText: "Reset 2FA",
		negativeText: "Cancel",
		onPositiveClick: () => {
			act(user, () => Api.users.resetTotp(user.id))
		}
	})
}

function confirmTemporaryPassword(user: TenantUser) {
	dialog.warning({
		title: `A temporary password for ${user.username}?`,
		content: "Their current password stops working. They sign in with the temporary one and choose their own.",
		positiveText: "Issue",
		negativeText: "Cancel",
		onPositiveClick: () => {
			issueTemporaryPassword(user)
		}
	})
}

async function issueTemporaryPassword(user: TenantUser) {
	busy.value = user.id
	try {
		const response = await Api.users.issueTemporaryPassword(user.id)
		const { delivery, temporary_password, email_problem } = response.data
		replace(response.data.user)
		showPassword(response.data.user, { delivery, temporary_password, email_problem }, false)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Could not issue a temporary password.")
	} finally {
		busy.value = null
	}
}

function showPassword(user: TenantUser, delivery: TemporaryPasswordDelivery, invited: boolean) {
	passwordFor.value = user
	passwordDelivery.value = delivery
	passwordForInvite.value = invited
	passwordOpen.value = true
}

function onInvited({ user, delivery }: { user: TenantUser; delivery: TemporaryPasswordDelivery }) {
	replace(user)
	showPassword(user, delivery, true)
}

onBeforeMount(() => {
	load()
})
</script>
