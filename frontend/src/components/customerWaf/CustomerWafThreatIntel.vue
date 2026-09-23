<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-2">
			<n-input v-model:value="query" size="small" clearable placeholder="Filter by IP or country" class="w-60!">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
			<n-checkbox v-model:checked="hideBlocked" size="small">Hide already blocked</n-checkbox>
			<span v-if="summary" class="text-tertiary ml-auto text-xs">
				{{ summary.total_ips.toLocaleString() }} IPs scored
				<template v-if="summary.window_days">over {{ summary.window_days }} days</template>
				<template v-if="summary.last_run_at">· updated {{ relative(summary.last_run_at) }}</template>
			</span>
		</div>

		<CustomerWafError v-if="error" :error />

		<section v-else class="border-default overflow-hidden rounded-lg border" :aria-busy="loading">
			<div
				class="bg-secondary border-default text-secondary grid grid-cols-[minmax(0,1.4fr)_minmax(0,1.6fr)_auto_auto] items-center gap-4 border-b px-3 py-2"
			>
				<span :class="SECTION_LABEL">IP</span>
				<span :class="SECTION_LABEL">Threat score</span>
				<span :class="SECTION_LABEL" class="hidden sm:block">Last seen</span>
				<span :class="SECTION_LABEL" class="text-right">Status</span>
			</div>
			<div v-if="loading" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 6" :key="n" :height="36" :sharp="false" class="rounded-md" />
			</div>
			<n-empty v-else-if="!visible.length" :description="entries.length ? 'No offender matches' : 'No offenders'" class="min-h-52 justify-center" />
			<ul v-else class="divide-border flex flex-col divide-y">
				<li
					v-for="e of visible"
					:key="e.ip_address"
					class="hover:bg-secondary/60 grid grid-cols-[minmax(0,1.4fr)_minmax(0,1.6fr)_auto_auto] items-center gap-4 px-3 py-2 transition-colors"
				>
					<div class="flex min-w-0 flex-col">
						<span class="truncate font-mono text-sm">{{ e.ip_address }}</span>
						<span class="text-secondary truncate text-xs">
							{{ flag(e.country_code) }} {{ e.country_name ?? e.country_code ?? "Unknown" }}
						</span>
					</div>
					<div class="flex min-w-0 flex-col gap-1">
						<div class="flex items-baseline justify-between gap-2 text-xs">
							<span class="text-default font-semibold tabular-nums">{{ e.threat_score }}</span>
							<span class="text-secondary tabular-nums">
								{{ e.block_count.toLocaleString() }} blocked / {{ e.total_events.toLocaleString() }}
							</span>
						</div>
						<div class="h-1.5 w-full overflow-hidden rounded-full" :style="{ background: trackColor }">
							<div
								class="h-full rounded-full"
								:style="{ width: `${Math.max(2, (e.threat_score / maxScore) * 100)}%`, background: markColor }"
							/>
						</div>
					</div>
					<n-tooltip>
						<template #trigger>
							<span class="text-secondary hidden text-xs whitespace-nowrap sm:block">{{ relative(e.last_seen_at) }}</span>
						</template>
						first seen {{ formatDate(e.first_seen_at, dFormats.datetime) }} · last seen
						{{ formatDate(e.last_seen_at, dFormats.datetime) }}
					</n-tooltip>
					<div class="flex justify-end">
						<n-tag v-if="e.is_blocked" size="small" round :bordered="false">
							<template #icon><Icon :name="BlockIcon" :size="12" /></template>
							blocked by WAF
						</n-tag>
						<n-button v-else-if="canBlock" size="tiny" type="error" secondary @click="openBlock(e.ip_address)">
							<template #icon><Icon :name="BlockIcon" :size="12" /></template>
							Block
						</n-button>
					</div>
				</li>
			</ul>
		</section>

		<CustomerWafBlockDialog
			v-model:show="showBlock"
			:customer-code
			:instances="[instance]"
			:initial-target="blockTarget"
			@blocked="emit('blocked')"
		/>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance, CustomerWafThreatIntelEntry, CustomerWafThreatIntelSummary } from "@/types/customer-waf"
import { NButton, NCheckbox, NEmpty, NInput, NSkeleton, NTag, NTooltip } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import { useWafChartColors } from "./chart-colors"
import CustomerWafBlockDialog from "./CustomerWafBlockDialog.vue"
import CustomerWafError from "./CustomerWafError.vue"
import { capabilitiesFromRoles, flag } from "./utils"

const { customerCode, instance } = defineProps<{ customerCode: string; instance: CustomerWafInstance }>()
const emit = defineEmits<{ (e: "blocked"): void }>()

const SearchIcon = "carbon:search"
const BlockIcon = "carbon:locked"
const dFormats = useSettingsStore().dateFormat
const { markColor, trackColor } = useWafChartColors()

const loading = ref(false)
const error = ref<ApiError | null>(null)
const summary = ref<CustomerWafThreatIntelSummary | null>(null)
const entries = ref<CustomerWafThreatIntelEntry[]>([])
const query = ref("")
const hideBlocked = ref(false)
const showBlock = ref(false)
const blockTarget = ref("")

const canBlock = computed(() => capabilitiesFromRoles(instance.last_verified_role).can_block)
const maxScore = computed(() => Math.max(1, ...entries.value.map(e => e.threat_score)))
const visible = computed(() => {
	const q = query.value.trim().toLowerCase()
	return entries.value.filter(
		e =>
			(!hideBlocked.value || !e.is_blocked) &&
			(!q ||
				e.ip_address.includes(q) ||
				(e.country_name ?? "").toLowerCase().includes(q) ||
				(e.country_code ?? "").toLowerCase() === q)
	)
})

const relative = (ts: string) => dayjs(ts).fromNow()

function openBlock(ip: string) {
	blockTarget.value = ip
	showBlock.value = true
}

onBeforeMount(() => {
	loading.value = true
	Api.customerWaf
		.getThreatIntel(customerCode, instance.id)
		.then(res => {
			summary.value = res.data.summary
			entries.value = res.data.entries
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
})
</script>
