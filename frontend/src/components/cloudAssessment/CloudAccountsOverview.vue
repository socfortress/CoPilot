<template>
	<div class="flex flex-col gap-4" data-testid="cloud-accounts-overview">
		<!-- The headline figures, over the accounts the filters keep. -->
		<dl class="bg-border border-default m-0 grid grid-cols-2 gap-px overflow-hidden rounded-lg border lg:grid-cols-4">
			<div v-for="tile of tiles" :key="tile.key" class="bg-default flex flex-col gap-1 px-4 py-3" :data-testid="`cloud-tile-${tile.key}`">
				<dt :class="SECTION_LABEL">{{ tile.label }}</dt>
				<dd class="m-0 flex items-baseline gap-2">
					<span class="text-default font-mono text-2xl font-semibold tabular-nums">{{ tile.value }}</span>
					<span v-if="tile.hint" class="text-tertiary text-xs">{{ tile.hint }}</span>
				</dd>
			</div>
		</dl>

		<div class="flex flex-wrap items-center gap-2">
			<n-select
				v-model:value="customerFilter"
				:options="customerOptions"
				multiple
				filterable
				clearable
				max-tag-count="responsive"
				placeholder="Every customer"
				class="w-72!"
				aria-label="Customers"
				data-testid="cloud-filter-customer"
			/>
			<n-select
				v-model:value="providerFilter"
				:options="providerOptions"
				clearable
				placeholder="Every provider"
				class="w-48!"
				aria-label="Provider"
			/>
			<n-input v-model:value="search" clearable placeholder="Search accounts" class="w-64!" aria-label="Search accounts">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>

		<n-alert v-if="error" type="error" :bordered="false">{{ errorText }}</n-alert>

		<section class="border-default bg-default overflow-hidden rounded-lg border" :aria-busy="loading">
			<div class="text-tertiary hidden items-center gap-4 px-4 py-2 lg:grid" :class="COLUMNS">
				<span :class="HEAD">Account</span>
				<span :class="HEAD">Customer</span>
				<span :class="HEAD">Last scan</span>
				<span :class="HEAD">Failing</span>
				<span :class="HEAD">Since the scan before</span>
				<span :class="HEAD">Next scan</span>
			</div>
			<div v-if="loading && !accounts.length" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 3" :key="n" :height="48" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!accounts.length && !error"
				description="No customer has a cloud account yet"
				class="py-10"
				data-testid="cloud-overview-empty"
			>
				<template #extra>
					<p class="text-secondary max-w-md text-sm">
						Add one under
						<b>Customers → a customer → Cloud Accounts</b>
						with a read-only credential.
					</p>
				</template>
			</n-empty>
			<n-empty v-else-if="!shown.length" description="No account matches the filters" class="py-10" />
			<div v-else class="divide-border border-default flex flex-col divide-y border-t">
				<button
					v-for="account of shown"
					:key="account.id"
					type="button"
					class="hover:bg-secondary/50 grid w-full items-center gap-x-4 gap-y-1.5 px-4 py-3 text-left transition-colors"
					:class="COLUMNS_ROW"
					:data-testid="`cloud-overview-row-${account.id}`"
					@click="emit('open', account)"
				>
					<span class="flex min-w-0 items-center gap-2.5">
						<CloudProviderLogo :provider="account.provider" :size="20" />
						<span class="flex min-w-0 flex-col">
							<span class="text-default truncate text-sm font-medium">
								<bdi>{{ account.name }}</bdi>
								<n-tag v-if="!account.enabled" size="tiny" :bordered="false" class="ml-1">disabled</n-tag>
							</span>
							<span class="text-tertiary truncate font-mono text-xs">{{ account.cloud_account ?? "—" }}</span>
						</span>
					</span>
					<span class="text-secondary truncate text-sm" :title="account.customer_code">
						<bdi>{{ customerNames[account.customer_code] ?? account.customer_code }}</bdi>
					</span>
					<span class="flex min-w-0 flex-wrap items-center gap-1.5">
						<template v-if="account.last_scan">
							<CloudScanStatusTag :status="account.last_scan.status" />
							<span class="text-tertiary text-xs">{{ relative(account.last_scan.completed_at ?? account.last_scan.queued_at) }}</span>
						</template>
						<span v-else class="text-tertiary text-xs">Never scanned</span>
					</span>
					<span class="min-w-0">
						<CloudSeverityTags v-if="account.last_completed_scan?.counts" :counts="account.last_completed_scan.counts" />
						<span v-else class="text-tertiary text-xs">—</span>
					</span>
					<span class="text-secondary font-mono text-xs tabular-nums">
						<span
							v-if="account.last_completed_scan?.counts && account.last_completed_scan.previous_scan_id === null"
							class="text-tertiary font-sans"
						>
							First scan
						</span>
						<template v-else-if="account.last_completed_scan?.counts">
							<span :class="account.last_completed_scan.counts.new_failed ? 'text-error' : ''">
								+{{ account.last_completed_scan.counts.new_failed }} new
							</span>
							·
							<span :class="account.last_completed_scan.counts.resolved_failed ? 'text-success' : ''">
								−{{ account.last_completed_scan.counts.resolved_failed }} resolved
							</span>
						</template>
						<template v-else>—</template>
					</span>
					<span class="text-tertiary text-xs">
						{{ account.next_scheduled_at ? formatDate(account.next_scheduled_at, dFormats.datetime) : "Not scheduled" }}
					</span>
				</button>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { CloudAccount, CloudProvider } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { NAlert, NEmpty, NInput, NSelect, NSkeleton, NTag } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CloudProviderLogo from "./CloudProviderLogo.vue"
import CloudScanStatusTag from "./CloudScanStatusTag.vue"
import CloudSeverityTags from "./CloudSeverityTags.vue"
import { expiryState, isActive, PROVIDER_LABELS, PROVIDERS } from "./utils"

const emit = defineEmits<{ (e: "open", account: CloudAccount): void }>()

const SearchIcon = "carbon:search"
const HEAD = "text-2xs font-medium tracking-[0.12em] uppercase"
// One grid for the head and every row, so the columns line up.
const COLUMNS = "grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1.5fr)_minmax(0,1.2fr)_minmax(0,0.9fr)]"
// Written out in full, not composed: Tailwind finds classes by reading the source.
const COLUMNS_ROW =
	"grid-cols-1 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1.5fr)_minmax(0,1.2fr)_minmax(0,0.9fr)]"
/** While a scan is under way the list is read again this often (and only while the page is shown). */
const POLL_MS = 15_000

const dFormats = useSettingsStore().dateFormat
const { globalCustomerCodes, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()

const loading = ref(false)
const error = ref<ApiError | null>(null)
const accounts = ref<CloudAccount[]>([])
const customerNames = ref<Record<string, string>>({})
const customerFilter = ref<string[]>([...globalCustomerCodes.value])
const providerFilter = ref<CloudProvider | null>(null)
const search = ref("")
let timer: ReturnType<typeof setInterval> | null = null

const errorText = computed(() => (error.value ? getApiErrorMessage(error.value) || "The accounts couldn't be read." : ""))
const customerOptions = computed(() =>
	[...new Set(accounts.value.map(account => account.customer_code))].map(code => ({
		label: customerNames.value[code] ? `${customerNames.value[code]} (${code})` : code,
		value: code
	}))
)
const providerOptions = PROVIDERS.map(provider => ({ label: PROVIDER_LABELS[provider], value: provider }))

const shown = computed(() => {
	const needle = search.value.trim().toLocaleLowerCase()
	return accounts.value.filter(
		account =>
			(!customerFilter.value.length || customerFilter.value.includes(account.customer_code)) &&
			(!providerFilter.value || account.provider === providerFilter.value) &&
			(!needle ||
				account.name.toLocaleLowerCase().includes(needle) ||
				(account.cloud_account ?? "").toLocaleLowerCase().includes(needle))
	)
})

const tiles = computed(() => {
	const list = shown.value
	const counts = list.map(account => account.last_completed_scan?.counts).filter(Boolean)
	const critical = counts.reduce((sum, item) => sum + (item?.failed_critical ?? 0), 0)
	const high = counts.reduce((sum, item) => sum + (item?.failed_high ?? 0), 0)
	return [
		{ key: "accounts", label: "Accounts", value: list.length, hint: `${list.filter(a => a.enabled).length} enabled` },
		{ key: "critical", label: "Failing critical / high", value: `${critical} / ${high}`, hint: "in the latest scans" },
		{ key: "running", label: "Scans under way", value: list.filter(a => isActive(a.last_scan?.status)).length, hint: "" },
		{
			key: "expiring",
			label: "Credentials expiring",
			value: list.filter(a => ["soon", "expired"].includes(expiryState(a))).length,
			hint: "within 30 days or past"
		}
	]
})

function relative(value: string | null): string {
	return value ? dayjs(value).fromNow() : ""
}

function load(quiet = false) {
	if (!quiet) loading.value = true
	error.value = null
	return Promise.all([
		Api.cloudAssessment.getAllAccounts(),
		quiet ? Promise.resolve(null) : Api.customers.getCustomers({}).catch(() => null) // names are a nicety
	])
		.then(([res, customers]) => {
			accounts.value = res.data.accounts
			if (customers) {
				customerNames.value = Object.fromEntries((customers.data.customers ?? []).map(c => [c.customer_code, c.customer_name]))
			}
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

// The sidebar's customers filter the list live; emptied, every customer shows again.
onGlobalCustomerFilterChange(codes => {
	customerFilter.value = codes
})

onBeforeMount(() => {
	void load()
	timer = setInterval(() => {
		if (document.visibilityState === "visible" && accounts.value.some(account => isActive(account.last_scan?.status))) {
			void load(true)
		}
	}, POLL_MS)
})

onBeforeUnmount(() => {
	if (timer) clearInterval(timer)
})
</script>
