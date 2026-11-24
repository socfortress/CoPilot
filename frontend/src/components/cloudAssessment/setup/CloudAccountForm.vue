<template>
	<n-modal
		v-model:show="show"
		preset="card"
		:title="account ? `Edit cloud account — ${account.name}` : 'Add cloud account'"
		:style="{ maxWidth: 'min(720px, 94vw)' }"
		segmented
		:mask-closable="!saving"
		data-testid="cloud-account-form"
	>
		<n-form label-placement="top" :show-feedback="false" class="flex flex-col gap-4" @submit.prevent>
			<!-- The provider is chosen once: an account's credential and settings belong to it. -->
			<div v-if="!account" class="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Provider">
				<button
					v-for="provider of PROVIDERS"
					:key="provider"
					type="button"
					role="radio"
					:aria-checked="form.provider === provider"
					class="border-default hover:border-primary flex flex-col items-center gap-2 rounded-lg border px-3 py-3 text-sm transition-colors"
					:class="form.provider === provider ? 'border-primary! bg-secondary' : ''"
					:data-testid="`cloud-provider-${provider}`"
					@click="pickProvider(provider)"
				>
					<CloudProviderLogo :provider :size="24" />
					<span>{{ PROVIDER_LABELS[provider] }}</span>
				</button>
			</div>

			<n-form-item label="Name" v-bind="feedbackFor('name')">
				<n-input v-model:value="form.name" :maxlength="100" placeholder="e.g. Production" data-testid="cloud-account-name" />
			</n-form-item>

			<!-- AWS -->
			<template v-if="form.provider === 'aws'">
				<n-form-item v-if="!account" label="Sign-in">
					<n-radio-group v-model:value="form.auth_method" name="aws-auth">
						<n-radio value="role">IAM role with an External ID (recommended)</n-radio>
						<n-radio value="access_keys">The account's own access keys</n-radio>
					</n-radio-group>
				</n-form-item>
				<template v-if="form.auth_method === 'role'">
					<n-form-item label="Role ARN" v-bind="feedbackFor('role_arn')">
						<n-input
							v-model:value="form.role_arn"
							class="font-mono"
							placeholder="arn:aws:iam::123456789012:role/ProwlerScan"
							data-testid="cloud-account-role-arn"
						/>
					</n-form-item>
					<p class="text-secondary -mt-3 text-xs">
						Prowler's read-only role in the customer's account. CoPilot generates the role's External ID when the
						account is saved, and shows how to create the role.
					</p>
					<n-form-item label="Assume the role with">
						<n-radio-group v-model:value="identity" name="aws-identity" data-testid="cloud-account-identity">
							<div class="flex flex-col gap-1.5">
								<n-radio value="keys">An IAM user's access keys</n-radio>
								<n-radio value="host">CoPilot's own AWS identity (an EC2 instance profile or ECS task role)</n-radio>
							</div>
						</n-radio-group>
					</n-form-item>
				</template>
				<template v-if="form.auth_method === 'access_keys' || !form.use_host_identity">
					<p class="text-secondary -mt-1 text-xs">
						{{
							form.auth_method === "role"
								? "The keys of the IAM user that assumes the role. It needs nothing but sts:AssumeRole on the role."
								: "Long-lived keys of an IAM user with the SecurityAudit and ViewOnlyAccess policies."
						}}
						Stored encrypted; never shown again.
					</p>
					<div class="grid gap-3 sm:grid-cols-2">
						<n-form-item label="Access key id" v-bind="feedbackFor('access_key_id')">
							<n-input
								v-model:value="form.access_key_id"
								class="font-mono"
								:placeholder="keepPlaceholder('AKIA…')"
								:input-props="{ autocomplete: 'off' }"
								data-testid="cloud-account-access-key-id"
							/>
						</n-form-item>
						<n-form-item
							label="Secret access key"
							v-bind="feedbackFor('secret_access_key')"
						>
							<n-input
								v-model:value="form.secret_access_key"
								type="password"
								show-password-on="click"
								class="font-mono"
								:placeholder="keepPlaceholder('')"
								:input-props="{ autocomplete: 'off' }"
								data-testid="cloud-account-secret-access-key"
							/>
						</n-form-item>
					</div>
				</template>
				<n-form-item label="Regions" v-bind="feedbackFor('regions')">
					<n-select
						v-model:value="form.regions"
						multiple
						filterable
						tag
						clearable
						:options="regionOptions"
						placeholder="Every region"
					/>
				</n-form-item>
			</template>

			<!-- Azure and Microsoft 365 -->
			<template v-else-if="form.provider === 'azure' || form.provider === 'm365'">
				<p class="text-secondary m-0 text-xs">
					An app registration in the customer's Entra ID, with
					{{
						form.provider === "azure"
							? "the Reader role on the subscriptions to scan"
							: "the Microsoft Graph and Exchange permissions Prowler lists"
					}}
					(see
					<a href="https://docs.prowler.com" target="_blank" rel="noopener noreferrer">Prowler's documentation</a>
					), and one of its client secrets.
				</p>
				<div class="grid gap-3 sm:grid-cols-2">
					<n-form-item label="Directory (tenant) id" v-bind="feedbackFor('tenant_id')">
						<n-input v-model:value="form.tenant_id" class="font-mono" placeholder="00000000-0000-0000-0000-000000000000" />
					</n-form-item>
					<n-form-item
						label="Application (client) id"
						v-bind="feedbackFor('client_id')"
					>
						<n-input v-model:value="form.client_id" class="font-mono" placeholder="00000000-0000-0000-0000-000000000000" />
					</n-form-item>
				</div>
				<n-form-item
					v-if="form.provider === 'm365'"
					label="Tenant domain"
					v-bind="feedbackFor('tenant_domain')"
				>
					<n-input v-model:value="form.tenant_domain" placeholder="contoso.onmicrosoft.com" />
				</n-form-item>
				<n-form-item label="Client secret" v-bind="feedbackFor('client_secret')">
					<n-input
						v-model:value="form.client_secret"
						type="password"
						show-password-on="click"
						class="font-mono"
						:placeholder="keepPlaceholder('The secret value, not its id')"
						:input-props="{ autocomplete: 'off' }"
						data-testid="cloud-account-client-secret"
					/>
				</n-form-item>
				<n-form-item label="Client secret expires">
					<n-date-picker v-model:value="form.secret_expires_at" type="date" clearable class="w-full" />
				</n-form-item>
				<p class="text-secondary -mt-3 text-xs">As Entra ID showed it: CoPilot warns a month before it lapses.</p>
				<n-form-item
					v-if="form.provider === 'azure'"
					label="Subscriptions"
					v-bind="feedbackFor('subscription_ids')"
				>
					<n-select
						v-model:value="form.subscription_ids"
						multiple
						filterable
						tag
						clearable
						:show-arrow="false"
						:options="[]"
						placeholder="Every subscription the app can read"
					/>
				</n-form-item>
			</template>

			<!-- Google Cloud -->
			<template v-else>
				<n-form-item label="Service account key" v-bind="feedbackFor('gcp_key_text')">
					<div class="flex w-full flex-col gap-2">
						<n-input
							v-model:value="form.gcp_key_text"
							type="textarea"
							class="font-mono text-xs"
							:autosize="{ minRows: 3, maxRows: 8 }"
							:placeholder="keepPlaceholder('Paste the key file\'s JSON, or upload it')"
							data-testid="cloud-account-gcp-key"
						/>
						<div>
							<n-button size="small" secondary @click="keyInput?.click()">
								<template #icon><Icon :name="UploadIcon" /></template>
								Upload key file
							</n-button>
							<input ref="keyInput" type="file" accept="application/json,.json" class="hidden" @change="readKeyFile" />
						</div>
					</div>
				</n-form-item>
				<p class="text-secondary -mt-3 text-xs">
					A key of a service account with the Viewer and Security Reviewer roles. Stored encrypted; never shown again.
				</p>
				<n-form-item label="Projects" v-bind="feedbackFor('project_ids')">
					<n-select
						v-model:value="form.project_ids"
						multiple
						filterable
						tag
						clearable
						:show-arrow="false"
						:options="[]"
						placeholder="Every project the key can read"
					/>
				</n-form-item>
				<div class="grid gap-3 sm:grid-cols-2">
					<n-form-item label="Projects to skip">
						<n-select
							v-model:value="form.excluded_project_ids"
							multiple
							filterable
							tag
							clearable
							:show-arrow="false"
							:options="[]"
						/>
					</n-form-item>
					<n-form-item
						label="Organization id"
						v-bind="feedbackFor('organization_id')"
					>
						<n-input v-model:value="form.organization_id" class="font-mono" placeholder="Optional" />
					</n-form-item>
				</div>
			</template>

			<!-- When to scan, and whether at all. -->
			<div class="border-default grid gap-3 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_auto]">
				<n-form-item label="Schedule">
					<div class="flex flex-wrap items-center gap-2">
						<n-select v-model:value="form.schedule" :options="SCHEDULE_OPTIONS" class="w-32!" />
						<template v-if="form.schedule !== 'off'">
							<n-select
								v-if="form.schedule === 'weekly'"
								v-model:value="form.schedule_weekday"
								:options="WEEKDAY_OPTIONS"
								class="w-36!"
								aria-label="Weekday"
							/>
							<span class="text-secondary text-sm">at</span>
							<n-select v-model:value="form.schedule_hour" :options="HOUR_OPTIONS" class="w-32!" aria-label="Hour (UTC)" />
						</template>
					</div>
				</n-form-item>
				<n-form-item label="Enabled" label-placement="left">
					<n-switch v-model:value="form.enabled" />
				</n-form-item>
			</div>

			<n-collapse v-model:expanded-names="expanded">
				<n-collapse-item title="Advanced" name="advanced">
					<div class="flex flex-col gap-3">
						<n-form-item label="Checks to skip" v-bind="feedbackFor('excluded_checks')">
							<n-select
								v-model:value="form.excluded_checks"
								multiple
								filterable
								tag
								clearable
								:show-arrow="false"
								:options="[]"
								placeholder="Prowler check ids, e.g. iam_root_hardware_mfa_enabled"
								data-testid="cloud-account-excluded-checks"
							/>
						</n-form-item>
						<n-form-item
							label="Services to skip"
							v-bind="feedbackFor('excluded_services')"
						>
							<n-select
								v-model:value="form.excluded_services"
								multiple
								filterable
								tag
								clearable
								:show-arrow="false"
								:options="[]"
								placeholder="Prowler service names, e.g. cloudtrail"
							/>
						</n-form-item>
						<n-form-item label="Stop a scan after (minutes)" v-bind="feedbackFor('timeout_minutes')">
							<n-input-number
								v-model:value="form.timeout_minutes"
								:min="5"
								:max="720"
								clearable
								placeholder="copilot-prowler's default"
								class="w-56"
							/>
						</n-form-item>
					</div>
				</n-collapse-item>
			</n-collapse>

			<n-alert v-if="error" type="error" :bordered="false" data-testid="cloud-account-form-error">
				{{ errorMessage }}
			</n-alert>
		</n-form>

		<template #footer>
			<div class="flex items-center justify-end gap-3">
				<span v-if="touched && Object.keys(problems).length" class="text-error mr-auto text-xs">
					Some fields need a look.
				</span>
				<n-button :disabled="saving" @click="show = false">Cancel</n-button>
				<n-button type="primary" :loading="saving" data-testid="cloud-account-save" @click="save()">
					{{ account ? "Save" : "Add account" }}
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { CloudAccount, CloudProvider } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import {
	NAlert,
	NButton,
	NCollapse,
	NCollapseItem,
	NDatePicker,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NModal,
	NRadio,
	NRadioGroup,
	NSelect,
	NSwitch
} from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CloudProviderLogo from "../CloudProviderLogo.vue"
import { PROVIDER_LABELS, PROVIDERS, WEEKDAYS } from "../utils"
import { AWS_REGIONS, createPayload, emptyForm, formFromAccount, formProblems, updatePayload } from "./accountForm"

const props = defineProps<{
	customerCode: string
	/** Editing this account; null adds a new one. */
	account: CloudAccount | null
}>()

const emit = defineEmits<{ (e: "saved", value: { account: CloudAccount; created: boolean }): void }>()

const show = defineModel<boolean>("show", { default: false })

const UploadIcon = "carbon:upload"
const SCHEDULE_OPTIONS = [
	{ label: "Off", value: "off" },
	{ label: "Daily", value: "daily" },
	{ label: "Weekly", value: "weekly" }
]
const WEEKDAY_OPTIONS = WEEKDAYS.map((label, value) => ({ label, value }))
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, hour) => ({ label: `${String(hour).padStart(2, "0")}:00 UTC`, value: hour }))
const regionOptions = AWS_REGIONS.map(region => ({ label: region, value: region }))

const form = ref(emptyForm())
const saving = ref(false)
const touched = ref(false)
const error = ref<ApiError | null>(null)
const keyInput = ref<HTMLInputElement | null>(null)
/** How an AWS role is assumed: an IAM user's keys, or CoPilot's host identity (no keys stored). */
const identity = computed<"keys" | "host">({
	get: () => (form.value.use_host_identity ? "host" : "keys"),
	set: value => {
		form.value.use_host_identity = value === "host"
	}
})
const expanded = ref<string[]>([])

/** The fields under Advanced: a problem with one opens it, or the message would be out of sight. */
const ADVANCED_FIELDS = ["excluded_checks", "excluded_services", "timeout_minutes"]

const problems = computed(() => (touched.value ? formProblems(form.value, props.account) : {}))
const errorMessage = computed(() => (error.value ? getApiErrorMessage(error.value) || "The account couldn't be saved." : ""))

/** A field's problem, shown under it only when it has one (the form shows no empty feedback rows). */
function feedbackFor(field: string) {
	const problem = problems.value[field]
	return { feedback: problem, validationStatus: problem ? ("error" as const) : undefined, showFeedback: !!problem }
}

/** On an edit, an empty credential field keeps the stored credential: the placeholder says so. */
function keepPlaceholder(fallback: string): string {
	return props.account?.secret_configured ? `${props.account.secret_hint ?? "Stored"} — leave blank to keep` : fallback
}

function pickProvider(provider: CloudProvider) {
	if (form.value.provider === provider) return
	form.value = { ...emptyForm(provider), name: form.value.name, schedule: form.value.schedule }
}

function readKeyFile(event: Event) {
	const file = (event.target as HTMLInputElement).files?.[0]
	if (!file) return
	file.text().then(text => {
		form.value.gcp_key_text = text
	})
	;(event.target as HTMLInputElement).value = ""
}

watch(show, open => {
	if (!open) return
	error.value = null
	touched.value = false
	expanded.value = []
	form.value = props.account ? formFromAccount(props.account) : emptyForm()
})

function save() {
	touched.value = true
	const found = Object.keys(formProblems(form.value, props.account))
	if (found.some(field => ADVANCED_FIELDS.includes(field))) expanded.value = ["advanced"]
	if (found.length) return
	saving.value = true
	error.value = null
	const request = props.account
		? Api.cloudAssessment.updateAccount(props.customerCode, props.account.id, updatePayload(form.value, props.account))
		: Api.cloudAssessment.createAccount(props.customerCode, createPayload(form.value))
	request
		.then(res => {
			emit("saved", { account: res.data.account, created: !props.account })
			// Write-only: the credential leaves the form as soon as it's saved.
			form.value.secret_access_key = ""
			form.value.client_secret = ""
			form.value.gcp_key_text = ""
			show.value = false
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			saving.value = false
		})
}
</script>
