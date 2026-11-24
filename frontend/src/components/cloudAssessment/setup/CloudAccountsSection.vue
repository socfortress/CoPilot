<template>
	<div class="flex flex-col gap-4" data-testid="cloud-accounts-section">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="text-lg font-bold">Cloud Accounts</h3>
				<p class="text-secondary max-w-3xl text-sm">
					AWS, Azure, Google Cloud and Microsoft 365 accounts CoPilot scans with Prowler. Set them up here; see their
					scans, findings and compliance under
					<b>Exposure → Cloud Security Assessment</b>
					<span>.</span>
				</p>
			</div>
			<n-button v-if="isAdmin && (accounts.length || loading)" type="primary" :disabled="!keyConfigured" @click="openForm(null)">
				<template #icon><Icon :name="AddIcon" /></template>
				Add account
			</n-button>
		</div>

		<n-alert v-if="!keyConfigured && !loading" type="warning" :bordered="false" data-testid="cloud-key-missing">
			Cloud credentials can't be saved until
			<code>CLOUD_ASSESSMENT_ENCRYPTION_KEY</code>
			is set in CoPilot's
			<code>.env</code>
			(it encrypts them). Generate one with
			<code>python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"</code>
			and restart the backend.
		</n-alert>
		<n-alert v-if="!runnerConfigured && !loading" type="warning" :bordered="false" data-testid="cloud-runner-missing">
			Scans need
			<code>PROWLER_RUNNER_TOKEN</code>
			(at least 32 characters, the same value for copilot-backend and copilot-prowler) in CoPilot's
			<code>.env</code>
			.
		</n-alert>
		<n-alert v-if="!isAdmin" type="info" :bordered="false" class="text-xs">
			Only administrators can add or change cloud accounts. Analysts can test them and start scans.
		</n-alert>
		<n-alert v-if="error" type="error" :bordered="false">{{ errorText(error) }}</n-alert>

		<n-spin :show="loading">
			<CustomerTabEmpty
				v-if="!accounts.length && !loading && !error"
				icon="carbon:cloud-monitoring"
				title="No cloud account for this customer yet"
				description="Connect the customer's AWS accounts, Azure subscriptions, Google Cloud projects or Microsoft 365 tenant. CoPilot scans them with Prowler, on demand or on a schedule, and keeps what each scan found."
				:points="EMPTY_POINTS"
				points-title="How it works"
				:note="isAdmin ? undefined : 'Only administrators can add cloud accounts.'"
			>
				<template v-if="isAdmin" #actions>
					<n-button type="primary" :disabled="!keyConfigured" data-testid="cloud-account-add" @click="openForm(null)">
						<template #icon><Icon :name="AddIcon" :size="16" /></template>
						Add account
					</n-button>
				</template>
			</CustomerTabEmpty>

			<div class="flex flex-col gap-3">
				<n-card v-for="account of accounts" :key="account.id" size="small" :data-testid="`cloud-account-${account.id}`">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="flex min-w-0 flex-col gap-1.5">
							<div class="flex flex-wrap items-center gap-2">
								<CloudProviderLogo :provider="account.provider" :size="18" />
								<span class="font-semibold">{{ account.name }}</span>
								<n-tag v-if="!account.enabled" size="small" :bordered="false">Disabled</n-tag>
								<n-tag v-if="expiryState(account) === 'expired'" size="small" type="error" :bordered="false">
									<template #icon><Icon :name="WarningIcon" :size="12" /></template>
									Credential expired
								</n-tag>
								<n-tag v-else-if="expiryState(account) === 'soon'" size="small" type="warning" :bordered="false">
									<template #icon><Icon :name="WarningIcon" :size="12" /></template>
									Credential expires in {{ account.secret_expires_in_days }} days
								</n-tag>
							</div>
							<div class="text-secondary text-xs">
								{{ PROVIDER_LABELS[account.provider] }} ·
								{{ CLOUD_ACCOUNT_LABELS[account.provider] }}
								<span class="font-mono">{{ account.cloud_account ?? "—" }}</span>
								· {{ AUTH_LABELS[account.auth_method] }}
								<template v-if="account.secret_hint">
									· credential
									<span class="font-mono">{{ account.secret_hint }}</span>
								</template>
							</div>
							<div class="text-secondary text-xs">
								{{ scheduleText(account) }}
								<template v-if="account.last_connection_test_at">
									· tested {{ formatDate(account.last_connection_test_at, dFormats.datetime) }}:
									<span :class="account.last_connection_ok ? 'text-success' : 'text-error'">
										{{ account.last_connection_ok ? "working" : "failed" }}
									</span>
								</template>
								<template v-else>· never tested</template>
							</div>
							<div v-if="account.last_scan" class="flex flex-wrap items-center gap-2 text-xs">
								<CloudScanStatusTag :status="account.last_scan.status" />
								<span class="text-secondary">
									{{ account.last_scan.trigger_type === "schedule" ? "scheduled" : "manual" }} scan,
									{{ relative(account.last_scan.completed_at ?? account.last_scan.queued_at) }}
								</span>
								<CloudSeverityTags v-if="account.last_completed_scan?.counts" :counts="account.last_completed_scan.counts" />
							</div>
						</div>
						<div class="flex flex-wrap gap-2">
							<n-button size="small" :loading="testing === account.id" @click="test(account)">Test connection</n-button>
							<n-button
								size="small"
								secondary
								type="primary"
								:disabled="!canScan(account) || !runnerConfigured"
								:loading="scanning === account.id"
								@click="scan(account)"
							>
								<template #icon><Icon :name="ScanIcon" /></template>
								Scan now
							</n-button>
							<n-button size="small" secondary @click="openPage(account)">
								<template #icon><Icon :name="OpenIcon" /></template>
								Open
							</n-button>
							<n-button v-if="account.auth_method === 'role'" size="small" secondary @click="setupFor = account">
								Role setup
							</n-button>
							<template v-if="isAdmin">
								<n-button size="small" secondary @click="openForm(account)">Edit</n-button>
								<n-popconfirm @positive-click="remove(account)">
									<template #trigger>
										<n-button size="small" secondary type="error" :loading="deleting === account.id">Delete</n-button>
									</template>
									Delete "{{ account.name }}" with its scans, findings and reports? Its credential stays valid in
									the cloud until you revoke it there.
								</n-popconfirm>
							</template>
						</div>
					</div>
					<n-alert
						v-if="testResults[account.id]"
						class="mt-3"
						:type="testResults[account.id]?.ok ? 'success' : 'error'"
						:bordered="false"
						:data-testid="`cloud-test-result-${account.id}`"
					>
						<div class="flex flex-col gap-1 text-xs">
							<span v-if="testResults[account.id]?.ok">The credentials work: Prowler signed in.</span>
							<template v-else>
								<span>{{ testResults[account.id]?.error_message ?? "The connection test failed." }}</span>
								<span v-if="testResults[account.id]?.prowler_error" class="opacity-80">
									Prowler raised
									<code>{{ testResults[account.id]?.prowler_error }}</code>
								</span>
							</template>
						</div>
					</n-alert>
				</n-card>
			</div>
		</n-spin>

		<CloudAccountForm v-model:show="showForm" :customer-code :account="editing" @saved="onSaved" />

		<n-modal
			:show="!!setupFor"
			preset="card"
			title="Create the ProwlerScan role"
			:auto-focus="false"
			:style="{ maxWidth: 'min(720px, 94vw)' }"
			segmented
			@update:show="open => !open && (setupFor = null)"
		>
			<AwsRoleSetup v-if="setupFor" :account="setupFor" :prowler-version="availability?.prowler_version ?? null" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CloudAccount, CloudConnectionTest } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { NAlert, NButton, NCard, NModal, NPopconfirm, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CustomerTabEmpty from "@/components/customers/CustomerTabEmpty.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CloudProviderLogo from "../CloudProviderLogo.vue"
import CloudScanStatusTag from "../CloudScanStatusTag.vue"
import CloudSeverityTags from "../CloudSeverityTags.vue"
import { useCloudAvailability } from "../useCloudAvailability"
import { AUTH_LABELS, canScan, CLOUD_ACCOUNT_LABELS, expiryState, PROVIDER_LABELS, scheduleText } from "../utils"
import AwsRoleSetup from "./AwsRoleSetup.vue"
import CloudAccountForm from "./CloudAccountForm.vue"

const { customerCode } = defineProps<{ customerCode: string }>()
const emit = defineEmits<{ (e: "changed"): void }>()

const AddIcon = "carbon:add"
const OpenIcon = "carbon:launch"
const ScanIcon = "carbon:play"
const WarningIcon = "carbon:warning-alt"
const EMPTY_POINTS = [
	{ title: "Add the account", description: "Its settings and a read-only credential, stored encrypted." },
	{ title: "Scan it", description: "On demand or daily/weekly, with Prowler in the copilot-prowler container." },
	{ title: "Read the results", description: "Findings, checks and compliance frameworks under Exposure." }
]

const router = useRouter()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)
const { availability, load: loadAvailability } = useCloudAvailability()

const loading = ref(false)
const error = ref<ApiError | null>(null)
const accounts = ref<CloudAccount[]>([])
const keyConfigured = ref(true)
const runnerConfigured = ref(true)
const testing = ref<number | null>(null)
const scanning = ref<number | null>(null)
const deleting = ref<number | null>(null)
const testResults = ref<Record<number, CloudConnectionTest>>({})
const showForm = ref(false)
const editing = ref<CloudAccount | null>(null)
const setupFor = ref<CloudAccount | null>(null)

function errorText(err: ApiError): string {
	return getApiErrorMessage(err) || "The request failed."
}

function relative(value: string | null): string {
	return value ? dayjs(value).fromNow() : ""
}

function load() {
	loading.value = true
	error.value = null
	Api.cloudAssessment
		.getAccounts(customerCode)
		.then(res => {
			accounts.value = res.data.accounts
			keyConfigured.value = res.data.encryption_key_configured
			runnerConfigured.value = res.data.runner_configured
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function replace(account: CloudAccount) {
	const index = accounts.value.findIndex(item => item.id === account.id)
	if (index === -1) accounts.value.push(account)
	else accounts.value[index] = account
}

function openForm(account: CloudAccount | null) {
	editing.value = account
	showForm.value = true
}

function onSaved(event: { account: CloudAccount; created: boolean }) {
	replace(event.account)
	delete testResults.value[event.account.id]
	message.success(`Cloud account "${event.account.name}" saved`)
	emit("changed")
	// A new role account can't be scanned until the role exists: show how to make it.
	if (event.created && event.account.auth_method === "role") setupFor.value = event.account
}

function test(account: CloudAccount) {
	testing.value = account.id
	Api.cloudAssessment
		.testConnection(customerCode, account.id)
		.then(res => {
			testResults.value[account.id] = res.data
			replace(res.data.account)
		})
		.catch((err: ApiError) => {
			message.error(errorText(err))
		})
		.finally(() => {
			testing.value = null
		})
}

function scan(account: CloudAccount) {
	scanning.value = account.id
	Api.cloudAssessment
		.startScan(customerCode, account.id)
		.then(res => {
			message.success(res.data.message)
			load()
		})
		.catch((err: ApiError) => {
			message.error(errorText(err))
		})
		.finally(() => {
			scanning.value = null
		})
}

// The scans and their findings live on the Cloud Security Assessment page; this section is setup.
function openPage(account: CloudAccount) {
	router.push({ name: "CloudSecurityAssessment", query: { customer: account.customer_code, account: String(account.id) } })
}

function remove(account: CloudAccount) {
	deleting.value = account.id
	Api.cloudAssessment
		.deleteAccount(customerCode, account.id)
		.then(res => {
			message.info(`Deleted "${account.name}" and ${res.data.scans_deleted} scan(s)`)
			accounts.value = accounts.value.filter(item => item.id !== account.id)
			emit("changed")
		})
		.catch((err: ApiError) => {
			message.error(errorText(err))
		})
		.finally(() => {
			deleting.value = null
		})
}

onBeforeMount(() => {
	load()
	loadAvailability()
})
</script>
