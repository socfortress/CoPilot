<template>
	<div class="flex flex-col gap-4" data-testid="cloud-account-detail">
		<div>
			<n-button text size="small" @click="emit('back')">
				<template #icon><Icon :name="BackIcon" /></template>
				All cloud accounts
			</n-button>
		</div>

		<n-alert v-if="error" type="error" :bordered="false">{{ errorText(error) }}</n-alert>
		<n-spin v-else :show="loading && !account" class="min-h-40">
			<template v-if="account">
				<!-- The account: identity and state on the first line, then its facts in one hairline grid. -->
				<section class="border-default bg-default overflow-hidden rounded-lg border" data-testid="cloud-account-panel">
					<div class="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
						<CloudProviderLogo :provider="account.provider" :size="22" />
						<h3 class="text-default m-0 min-w-0 truncate text-base font-semibold"><bdi>{{ account.name }}</bdi></h3>
						<n-tag v-if="!account.enabled" size="small" round :bordered="false">disabled</n-tag>
						<n-tag v-if="expiry === 'expired'" size="small" type="error" round :bordered="false">
							<template #icon><Icon :name="WarningIcon" :size="12" /></template>
							credential expired
						</n-tag>
						<n-tag v-else-if="expiry === 'soon'" size="small" type="warning" round :bordered="false">
							<template #icon><Icon :name="WarningIcon" :size="12" /></template>
							credential expires in {{ account.secret_expires_in_days }} days
						</n-tag>
						<div class="ml-auto flex flex-wrap gap-2">
							<n-button size="small" :loading="testing" @click="test()">Test connection</n-button>
							<n-button
								size="small"
								type="primary"
								:disabled="!canScan(account)"
								:loading="starting"
								data-testid="cloud-scan-now"
								@click="scanNow()"
							>
								<template #icon><Icon :name="ScanIcon" /></template>
								Scan now
							</n-button>
							<n-button size="small" secondary @click="routeCustomer({ code: customerCode, tab: 'Cloud Accounts' }).navigate()">
								<template #icon><Icon :name="SettingsIcon" /></template>
								{{ isAdmin ? "Configure" : "Settings" }}
							</n-button>
						</div>
					</div>
					<!-- Three to a row: a tenant id or a weekly schedule needs the room, and is never cut. -->
					<dl class="bg-border border-default m-0 grid grid-cols-1 gap-px border-t sm:grid-cols-2 lg:grid-cols-3">
						<div v-for="fact of facts" :key="fact.key" class="bg-default flex min-w-0 flex-col gap-1 px-4 py-2.5">
							<dt class="text-tertiary text-2xs font-medium tracking-[0.12em] uppercase">{{ fact.label }}</dt>
							<dd class="m-0 flex min-w-0 flex-wrap items-baseline gap-x-2 text-sm" :title="fact.title">
								<span class="min-w-0" :class="fact.mono ? 'font-mono text-xs break-all' : 'text-default break-words'">
									{{ fact.value }}
								</span>
								<span v-if="fact.hint" class="text-tertiary text-xs">{{ fact.hint }}</span>
							</dd>
						</div>
					</dl>
					<n-alert
						v-if="testResult"
						:type="testResult.ok ? 'success' : 'error'"
						:bordered="false"
						class="border-default rounded-none! border-t"
						data-testid="cloud-test-result"
					>
						<template v-if="testResult.ok">The credentials work: Prowler signed in.</template>
						<template v-else>
							{{ testResult.error_message ?? "The connection test failed." }}
							<span v-if="testResult.prowler_error" class="opacity-80">
								Prowler raised
								<code>{{ testResult.prowler_error }}</code>
							</span>
						</template>
					</n-alert>
				</section>

				<!-- The scans, newest first: picking one shows it below. -->
				<section class="border-default bg-default mt-4 overflow-hidden rounded-lg border" data-testid="cloud-scans">
					<header class="bg-secondary border-default flex flex-wrap items-baseline justify-between gap-2 border-b px-4 py-2">
						<span :class="SECTION_LABEL">Scans</span>
						<span class="text-secondary text-2xs font-mono tabular-nums">{{ totalScans }} in all</span>
					</header>
					<n-empty v-if="!scans.length" description="Never scanned: Scan now starts the first scan" class="py-8" />
					<div v-else class="divide-border flex flex-col divide-y">
						<button
							v-for="scan of visibleScans"
							:key="scan.id"
							type="button"
							class="hover:bg-secondary/50 grid w-full grid-cols-[auto_minmax(0,1fr)] items-center gap-x-4 gap-y-1 border-l-2 px-4 py-2.5 text-left transition-colors sm:grid-cols-[8.5rem_11rem_minmax(0,1fr)_auto]"
							:class="scan.id === selectedScan?.id ? 'border-l-primary bg-secondary/40' : 'border-l-transparent'"
							:data-testid="`cloud-scan-row-${scan.id}`"
							@click="selectScan(scan.id)"
						>
							<CloudScanStatusTag :status="scan.status" class="justify-self-start" />
							<span class="text-secondary text-xs">
								{{ formatDate(scan.started_at ?? scan.queued_at ?? "", dFormats.datetime) }}
							</span>
							<span class="text-secondary col-span-2 truncate text-xs sm:col-span-1" :title="scanOutcome(scan)">
								{{ scanOutcome(scan) }}
							</span>
							<span class="text-tertiary hidden text-xs sm:block">
								{{ scan.trigger_type === "schedule" ? "scheduled" : (scan.requested_by ?? "manual") }}
							</span>
						</button>
						<button
							v-if="scans.length > COLLAPSED_SCANS"
							type="button"
							class="text-primary px-4 py-2 text-left text-xs"
							@click="showAllScans = !showAllScans"
						>
							{{ showAllScans ? "Show fewer" : `Show all ${scans.length}` }}
						</button>
					</div>
				</section>

				<CloudScanView
					v-if="selectedScan"
					:key="selectedScan.id"
					class="mt-4"
					:customer-code
					:account
					:scan="selectedScan"
					@changed="reload()"
				/>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CloudAccount, CloudConnectionTest, CloudScan } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { NAlert, NButton, NEmpty, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useNavigation, useRouteQueryParam } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CloudProviderLogo from "./CloudProviderLogo.vue"
import CloudScanStatusTag from "./CloudScanStatusTag.vue"
import CloudScanView from "./CloudScanView.vue"
import {
	AUTH_LABELS,
	AUTH_SHORT_LABELS,
	canScan,
	CLOUD_ACCOUNT_LABELS,
	expiryState,
	isActive,
	PROVIDER_LABELS,
	scanOutcome,
	scheduleText
} from "./utils"

const { customerCode, accountId } = defineProps<{ customerCode: string; accountId: number }>()
const emit = defineEmits<{ (e: "back"): void }>()

const BackIcon = "carbon:arrow-left"
const ScanIcon = "carbon:play"
const SettingsIcon = "carbon:settings"
const WarningIcon = "carbon:warning-alt"
const COLLAPSED_SCANS = 8
/** While a scan is under way the account and its scans are read again this often. */
const POLL_MS = 10_000

const route = useRoute()
const router = useRouter()
const message = useMessage()
const { routeCustomer } = useNavigation()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)
const scanQuery = useRouteQueryParam("scan")

const loading = ref(false)
const error = ref<ApiError | null>(null)
const account = ref<CloudAccount | null>(null)
const scans = ref<CloudScan[]>([])
const totalScans = ref(0)
const showAllScans = ref(false)
const testing = ref(false)
const starting = ref(false)
const testResult = ref<CloudConnectionTest | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

const expiry = computed(() => (account.value ? expiryState(account.value) : "unknown"))
const visibleScans = computed(() => (showAllScans.value ? scans.value : scans.value.slice(0, COLLAPSED_SCANS)))

/** The scan the URL names, else the newest completed one, else the newest. */
const selectedScan = computed<CloudScan | null>(() => {
	const named = scans.value.find(scan => String(scan.id) === scanQuery.value)
	return named ?? scans.value.find(scan => scan.status === "completed") ?? scans.value[0] ?? null
})

const facts = computed(() => {
	const current = account.value
	if (!current) return []
	const tested = current.last_connection_test_at
	return [
		{ key: "customer", label: "Customer", value: current.customer_code, hint: null, mono: false, title: undefined },
		{
			key: "cloud",
			label: CLOUD_ACCOUNT_LABELS[current.provider],
			value: current.cloud_account ?? "—",
			hint: PROVIDER_LABELS[current.provider],
			mono: true,
			title: undefined
		},
		{
			key: "auth",
			label: "Sign-in",
			value: AUTH_SHORT_LABELS[current.auth_method],
			hint: current.auth_method === "role" && !current.secret_configured ? "CoPilot's own identity" : null,
			mono: false,
			title: AUTH_LABELS[current.auth_method]
		},
		{
			key: "credential",
			label: "Credential",
			value: current.secret_hint ?? (current.secret_configured ? "stored" : "none stored"),
			hint: current.secret_expires_at ? `expires ${formatDate(current.secret_expires_at, dFormats.date)}` : null,
			mono: !!current.secret_hint,
			title: undefined
		},
		{
			key: "schedule",
			label: "Schedule",
			value: scheduleText(current),
			hint: current.next_scheduled_at ? `next ${dayjs(current.next_scheduled_at).fromNow()}` : null,
			mono: false,
			title: undefined
		},
		{
			key: "tested",
			label: "Connection",
			value: tested ? (current.last_connection_ok ? "working" : "failed") : "never tested",
			hint: tested ? dayjs(tested).fromNow() : null,
			mono: false,
			title: tested && !current.last_connection_ok ? (current.last_connection_message ?? undefined) : undefined
		}
	]
})

function errorText(err: ApiError): string {
	return getApiErrorMessage(err) || "The request failed."
}

function selectScan(scanId: number) {
	router.replace({ query: { ...route.query, scan: String(scanId), framework: undefined, check: undefined } })
}

function reload(quiet = false) {
	if (!quiet) loading.value = true
	return Promise.all([
		Api.cloudAssessment.getAccount(customerCode, accountId),
		Api.cloudAssessment.getScans(customerCode, { account_id: accountId, page_size: 100 })
	])
		.then(([accountRes, scansRes]) => {
			account.value = accountRes.data.account
			scans.value = scansRes.data.scans
			totalScans.value = scansRes.data.total
			error.value = null
		})
		.catch((err: ApiError) => {
			if (!quiet) error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function test() {
	testing.value = true
	testResult.value = null
	Api.cloudAssessment
		.testConnection(customerCode, accountId)
		.then(res => {
			testResult.value = res.data
			account.value = res.data.account
		})
		.catch((err: ApiError) => {
			message.error(errorText(err))
		})
		.finally(() => {
			testing.value = false
		})
}

function scanNow() {
	starting.value = true
	Api.cloudAssessment
		.startScan(customerCode, accountId)
		.then(res => {
			message.success(res.data.message)
			return reload(true).then(() => selectScan(res.data.scan.id))
		})
		.catch((err: ApiError) => {
			message.error(errorText(err))
		})
		.finally(() => {
			starting.value = false
		})
}

onBeforeMount(() => {
	void reload()
	timer = setInterval(() => {
		if (document.visibilityState === "visible" && scans.value.some(scan => isActive(scan.status))) void reload(true)
	}, POLL_MS)
})

onBeforeUnmount(() => {
	if (timer) clearInterval(timer)
})
</script>
