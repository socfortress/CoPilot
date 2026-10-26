<template>
	<n-modal v-model:show="show" preset="card" :title="$t('users.invite.title')" class="max-w-120!" data-testid="invite-dialog">
		<form class="flex flex-col gap-4" novalidate @submit.prevent="submit()">
			<p class="text-secondary m-0 text-sm">
				{{ smtpConfigured ? $t("users.invite.introEmail") : $t("users.invite.introShown") }}
			</p>

			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">{{ $t("users.invite.username") }}</span>
				<n-input
					v-model:value="form.username"
					:status="shownProblems.username ? 'error' : undefined"
					placeholder="jane.doe"
					:maxlength="64"
					:input-props="{ autocomplete: 'off' }"
					data-testid="invite-username"
				/>
				<span v-if="shownProblems.username" class="text-error text-xs" data-testid="invite-username-problem">
					{{ shownProblems.username }}
				</span>
			</label>

			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">{{ $t("users.invite.email") }}</span>
				<n-input
					v-model:value="form.email"
					:status="shownProblems.email ? 'error' : undefined"
					placeholder="jane.doe@example.com"
					:input-props="{ type: 'email', autocomplete: 'off' }"
					data-testid="invite-email"
				/>
				<span v-if="shownProblems.email" class="text-error text-xs" data-testid="invite-email-problem">
					{{ shownProblems.email }}
				</span>
			</label>

			<!-- Only a choice when there is one: a single administered customer is the invitation's. -->
			<label v-if="customers.length > 1" class="flex flex-col gap-1">
				<span class="text-secondary text-xs">{{ $t("users.invite.customers") }}</span>
				<n-select
					v-model:value="form.customerCodes"
					multiple
					:options="customerOptions"
					:status="shownProblems.customerCodes ? 'error' : undefined"
					data-testid="invite-customers"
				/>
				<span v-if="shownProblems.customerCodes" class="text-error text-xs">
					{{ shownProblems.customerCodes }}
				</span>
			</label>
			<i18n-t
				v-else-if="customers.length === 1"
				keypath="users.invite.willSee"
				tag="p"
				scope="global"
				class="text-secondary m-0 text-sm"
			>
				<template #customer>
					<b>{{ customers[0]?.customer_name }}</b>
				</template>
			</i18n-t>

			<n-alert v-if="error" type="error" :bordered="false" data-testid="invite-error">{{ error }}</n-alert>

			<div class="flex justify-end gap-2">
				<n-button :disabled="sending" @click="show = false">{{ $t("common.actions.cancel") }}</n-button>
				<n-button type="primary" attr-type="submit" :loading="sending" data-testid="invite-submit">
					{{ $t("users.invite.submit") }}
				</n-button>
			</div>
		</form>
	</n-modal>
</template>

<script setup lang="ts">
import type { InviteForm } from "./users"
import type { PortalCustomer } from "@/types/auth"
import type { ApiError } from "@/types/common"
import type { TemporaryPasswordDelivery, TenantUser } from "@/types/users"
import { NAlert, NButton, NInput, NModal, NSelect } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import { inviteProblems } from "./users"

/**
 * Invite a portal user to customers the caller administers (#1296). The API checks everything
 * again; the form says what it would refuse before sending.
 */

const { customers, smtpConfigured } = defineProps<{
	customers: PortalCustomer[]
	smtpConfigured: boolean
}>()
const emit = defineEmits<{
	(e: "invited", value: { user: TenantUser; delivery: TemporaryPasswordDelivery }): void
}>()
const show = defineModel<boolean>("show", { required: true })
const { t } = useI18n()
const form = ref<InviteForm>({ username: "", email: "", customerCodes: [] })
const submitted = ref(false)
const sending = ref(false)
const error = ref<string | null>(null)

const customerOptions = computed(() => customers.map(c => ({ label: c.customer_name, value: c.customer_code })))
const problems = computed(() => inviteProblems(form.value))
// Problems show once the user has tried to send: an empty form is not an error.
const shownProblems = computed(() => (submitted.value ? problems.value : {}))

watch(show, open => {
	if (!open) return
	form.value = { username: "", email: "", customerCodes: customers.length === 1 ? [customers[0]!.customer_code] : [] }
	submitted.value = false
	error.value = null
})

async function submit() {
	submitted.value = true
	error.value = null
	if (Object.keys(problems.value).length) return
	sending.value = true
	try {
		const response = await Api.users.invite({
			username: form.value.username.trim(),
			email: form.value.email.trim(),
			customer_codes: form.value.customerCodes
		})
		const { user, delivery, temporary_password, email_problem } = response.data
		emit("invited", { user, delivery: { delivery, temporary_password, email_problem } })
		show.value = false
	} catch (err) {
		error.value = getApiErrorMessage(err as ApiError) || t("users.invite.failed")
	} finally {
		sending.value = false
	}
}
</script>
