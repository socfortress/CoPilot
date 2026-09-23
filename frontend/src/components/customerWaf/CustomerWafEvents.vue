<template>
	<div class="flex flex-col gap-3">
		<!-- Filters in one row above the results. -->
		<div class="flex flex-wrap items-center gap-2">
			<n-radio-group v-model:value="action" size="small" @update:value="load(0)">
				<n-radio-button v-for="o of actionOptions" :key="o.label" :value="o.value">{{ o.label }}</n-radio-button>
			</n-radio-group>
			<n-input
				v-model:value="clientIp"
				size="small"
				clearable
				placeholder="Client IP"
				class="w-48! font-mono"
				@keyup.enter="load(0)"
				@clear="clearIp()"
			>
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
			<n-button size="small" secondary :loading @click="load(0)">Apply</n-button>
			<span class="text-tertiary ml-auto text-xs">newest first · {{ limit }} per page</span>
		</div>

		<CustomerWafError v-if="error" :error />

		<section v-else class="border-default overflow-hidden rounded-lg border" :aria-busy="loading">
			<div v-if="loading && !events.length" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 6" :key="n" :height="40" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!events.length"
				description="No events match these filters"
				class="min-h-52 justify-center"
			/>
			<ul v-else class="divide-border flex flex-col divide-y" :class="{ 'opacity-60': loading }">
				<li v-for="e of events" :key="e.id" class="hover:bg-secondary/60 transition-colors">
					<button
						type="button"
						class="grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 px-3 py-2 text-left"
						:aria-expanded="expanded.has(e.id)"
						@click="toggle(e.id)"
					>
						<WafActionPill :action="e.action" />
						<div class="flex min-w-0 flex-col">
							<div class="flex min-w-0 items-center gap-2 text-sm">
								<span class="bg-secondary border-default rounded border px-1.5 font-mono text-2xs">
									{{ e.method }}
								</span>
								<span class="truncate">
									<span class="text-secondary">{{ e.host }}</span>
									<span class="font-mono text-xs">{{ e.uri }}</span>
								</span>
							</div>
							<div class="text-secondary flex flex-wrap items-center gap-x-3 text-xs">
								<span class="font-mono">{{ e.client_ip }}</span>
								<span v-if="e.geoip_country_code">
									{{ flag(e.geoip_country_code) }}
									{{ e.geoip_country_name ?? e.geoip_country_code }}
								</span>
								<span v-if="e.matched_rules[0]?.msg" class="truncate">{{ e.matched_rules[0].msg }}</span>
							</div>
						</div>
						<div class="flex flex-col items-end gap-0.5 text-xs">
							<n-tooltip>
								<template #trigger>
									<span class="text-secondary whitespace-nowrap">{{ relative(e.timestamp) }}</span>
								</template>
								{{ formatDate(e.timestamp, dFormats.datetimesec) }}
							</n-tooltip>
							<span v-if="e.anomaly_score != null" class="text-tertiary tabular-nums">
								score {{ e.anomaly_score }}
							</span>
						</div>
					</button>
					<div v-if="expanded.has(e.id)" class="bg-secondary border-default flex flex-col gap-2 border-t px-3 py-3">
						<div class="grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
							<div><span class="text-secondary">Transaction</span> <span class="font-mono">{{ e.transaction_id }}</span></div>
							<div><span class="text-secondary">Severity</span> {{ e.severity ?? "—" }}</div>
							<div><span class="text-secondary">Rule</span> <span class="font-mono">{{ e.rule_id ?? "—" }}</span></div>
							<div v-if="e.geoip_city"><span class="text-secondary">City</span> {{ e.geoip_city }}</div>
						</div>
						<div v-if="e.matched_rules.length" class="flex flex-col gap-1">
							<span :class="SECTION_LABEL">Matched rules</span>
							<div
								v-for="m of e.matched_rules"
								:key="`${m.id}-${m.msg}`"
								class="flex items-baseline gap-2 text-xs"
							>
								<span class="font-mono text-secondary w-16 shrink-0">{{ m.id ?? "—" }}</span>
								<span>{{ m.msg ?? "" }}</span>
							</div>
						</div>
					</div>
				</li>
			</ul>
		</section>

		<div class="flex items-center justify-end gap-2 text-xs">
			<span class="text-secondary tabular-nums">
				{{ events.length ? `${offset + 1}–${offset + events.length}` : "0" }}
			</span>
			<n-button-group size="small">
				<n-button secondary :disabled="offset === 0 || loading" @click="load(Math.max(0, offset - limit))">
					<template #icon><Icon :name="PrevIcon" /></template>
					Newer
				</n-button>
				<n-button secondary :disabled="events.length < limit || loading" icon-placement="right" @click="load(offset + limit)">
					<template #icon><Icon :name="NextIcon" /></template>
					Older
				</n-button>
			</n-button-group>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafAction, CustomerWafEvent, CustomerWafInstance } from "@/types/customer-waf"
import {
	NButton,
	NButtonGroup,
	NEmpty,
	NInput,
	NRadioButton,
	NRadioGroup,
	NSkeleton,
	NTooltip
} from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CustomerWafError from "./CustomerWafError.vue"
import { flag } from "./utils"
import WafActionPill from "./WafActionPill.vue"

const { customerCode, instance, initialClientIp } = defineProps<{
	customerCode: string
	instance: CustomerWafInstance
	/** Pre-filter, e.g. from "Events from this IP" on the Overview. */
	initialClientIp?: string | null
}>()

const SearchIcon = "carbon:search"
const PrevIcon = "carbon:chevron-left"
const NextIcon = "carbon:chevron-right"
const dFormats = useSettingsStore().dateFormat
const limit = 50
// "all" rather than null: radio buttons need a real value.
const actionOptions: { label: string; value: CustomerWafAction | "all" }[] = [
	{ label: "All", value: "all" },
	{ label: "Blocked", value: "blocked" },
	{ label: "Detected", value: "detected" },
	{ label: "Passed", value: "passed" }
]

const loading = ref(false)
const error = ref<ApiError | null>(null)
const events = ref<CustomerWafEvent[]>([])
const offset = ref(0)
const action = ref<CustomerWafAction | "all">("all")
const clientIp = ref<string | null>(initialClientIp ?? null)
const expanded = ref(new Set<string>())

const relative = (ts: string) => dayjs(ts).fromNow()

function toggle(id: string) {
	const next = new Set(expanded.value)
	if (next.has(id)) next.delete(id)
	else next.add(id)
	expanded.value = next
}

function clearIp() {
	clientIp.value = null
	load(0)
}

function load(nextOffset: number) {
	loading.value = true
	error.value = null
	Api.customerWaf
		.getEvents(customerCode, instance.id, {
			action: action.value === "all" ? null : action.value,
			client_ip: clientIp.value?.trim() || null,
			limit,
			offset: nextOffset
		})
		.then(res => {
			events.value = res.data.events
			offset.value = nextOffset
			expanded.value = new Set()
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => load(0))
</script>
