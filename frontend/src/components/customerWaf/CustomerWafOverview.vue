<template>
	<div class="flex flex-col gap-4" :aria-busy="loading">
		<CustomerWafError v-if="error" :error />

		<!-- Skeleton mirrors the real layout so nothing jumps when data lands. -->
		<template v-else-if="loading && !stats">
			<n-skeleton :height="112" :sharp="false" class="rounded-lg" />
			<n-skeleton :height="260" :sharp="false" class="rounded-lg" />
			<div class="grid gap-4 md:grid-cols-2">
				<n-skeleton v-for="n of 4" :key="n" :height="200" :sharp="false" class="rounded-lg" />
			</div>
		</template>

		<template v-else-if="stats">
			<!-- Last hour: one fact grid, hairlines between cells (File Analysis's pattern). -->
			<section class="border-default overflow-hidden rounded-lg border">
				<header class="bg-secondary border-default flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
					<span :class="SECTION_LABEL">Last hour</span>
					<div class="flex flex-wrap items-center gap-2">
						<Badge type="splitted" size="small" :color="stats.caddy_healthy === false ? 'danger' : 'success'">
							<template #iconLeft>
								<Icon :name="stats.caddy_healthy === false ? AlertIcon : HealthyIcon" :size="12" />
							</template>
							<template #value>engine {{ stats.caddy_healthy === false ? "unhealthy" : "healthy" }}</template>
						</Badge>
						<Badge v-if="stats.ingestion_lag_seconds != null" type="splitted" size="small">
							<template #iconLeft><Icon :name="LagIcon" :size="12" /></template>
							<template #label>ingest lag</template>
							<template #value>{{ formatLag(stats.ingestion_lag_seconds) }}</template>
						</Badge>
						<Badge v-if="stats.events_per_minute != null" type="splitted" size="small">
							<template #iconLeft><Icon :name="RateIcon" :size="12" /></template>
							<template #value>{{ stats.events_per_minute.toFixed(1) }} events/min</template>
						</Badge>
					</div>
				</header>
				<div class="bg-border grid grid-cols-2 gap-px lg:grid-cols-4">
					<div v-for="fact of facts" :key="fact.label" class="bg-default flex min-h-24 flex-col gap-1 p-4">
						<span :class="SECTION_LABEL">{{ fact.label }}</span>
						<span class="text-2xl leading-none font-semibold tabular-nums" :class="fact.accent">
							{{ fact.value }}
						</span>
						<span class="text-secondary text-xs">{{ fact.hint }}</span>
					</div>
				</div>
			</section>

			<section class="border-default overflow-hidden rounded-lg border">
				<header class="bg-secondary border-default flex items-baseline justify-between gap-2 border-b px-3 py-2">
					<span :class="SECTION_LABEL">Requests per hour</span>
					<span class="text-tertiary text-2xs">last 24h · peak {{ peak.toLocaleString() }}/h</span>
				</header>
				<div class="p-3">
					<WafRequestsChart :points="stats.requests_per_hour" />
				</div>
			</section>

			<div class="grid gap-4 md:grid-cols-2">
				<WafRankList
					title="Attack categories"
					caption="last hour · blocked + detected"
					:items="categories"
					empty-text="No attacks in the last hour"
				/>
				<WafRankList title="Top countries" caption="last 24h · all requests" :items="countries">
					<template #label="{ item }">
						<span class="text-base leading-none">{{ flag(item.code as string | null) }}</span>
						<span class="truncate">{{ item.label }}</span>
					</template>
				</WafRankList>
				<WafRankList
					title="Top rules"
					caption="last hour"
					:items="rules"
					mono
					empty-text="No rule fired in the last hour"
				/>
				<WafRankList title="Top client IPs" caption="last hour" :items="ips" mono>
					<template #actions="{ item }">
						<n-tooltip>
							<template #trigger>
								<n-button
									size="tiny"
									quaternary
									class="opacity-60 group-hover:opacity-100"
									@click="emit('viewEvents', item.label)"
								>
									<template #icon><Icon :name="EventsIcon" :size="14" /></template>
								</n-button>
							</template>
							Events from this IP
						</n-tooltip>
						<n-tooltip v-if="canBlock">
							<template #trigger>
								<n-button
									size="tiny"
									quaternary
									type="error"
									class="opacity-60 group-hover:opacity-100"
									@click="openBlock(item.label)"
								>
									<template #icon><Icon :name="BlockIcon" :size="14" /></template>
								</n-button>
							</template>
							Block at WAF
						</n-tooltip>
					</template>
				</WafRankList>
			</div>
		</template>

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
import type { WafRankItem } from "./WafRankList.vue"
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance, CustomerWafStats } from "@/types/customer-waf"
import { NButton, NSkeleton, NTooltip } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import CustomerWafBlockDialog from "./CustomerWafBlockDialog.vue"
import CustomerWafError from "./CustomerWafError.vue"
import { capabilitiesFromRoles, flag } from "./utils"
import WafRankList from "./WafRankList.vue"
import WafRequestsChart from "./WafRequestsChart.vue"

const { customerCode, instance } = defineProps<{ customerCode: string; instance: CustomerWafInstance }>()
const emit = defineEmits<{
	(e: "viewEvents", clientIp: string): void
	(e: "blocked"): void
}>()

const HealthyIcon = "carbon:checkmark-filled"
const AlertIcon = "carbon:warning-alt-filled"
const LagIcon = "carbon:time"
const RateIcon = "carbon:activity"
const EventsIcon = "carbon:list"
const BlockIcon = "carbon:locked"

const loading = ref(false)
const error = ref<ApiError | null>(null)
const stats = ref<CustomerWafStats | null>(null)
const showBlock = ref(false)
const blockTarget = ref("")

const canBlock = computed(() => capabilitiesFromRoles(instance.last_verified_role).can_block)
const peak = computed(() => Math.max(0, ...(stats.value?.requests_per_hour.map(h => h.count) ?? [0])))

const facts = computed(() => {
	const s = stats.value
	if (!s) return []
	const pct = (s.block_rate * 100).toFixed(1) // the WAF reports block_rate as a fraction
	return [
		{ label: "Requests", value: s.total_1h.toLocaleString(), hint: "inspected by the WAF", accent: "text-default" },
		{
			label: "Blocked",
			value: s.blocked_1h.toLocaleString(),
			hint: `${pct}% of requests`,
			accent: s.blocked_1h > 0 ? "text-error" : "text-default"
		},
		{
			label: "Detected",
			value: s.detected_1h.toLocaleString(),
			hint: "matched but let through",
			accent: s.detected_1h > 0 ? "text-warning" : "text-default"
		},
		{
			label: "Attack types",
			value: s.attack_categories.length.toLocaleString(),
			hint: s.attack_categories[0] ? `most: ${s.attack_categories[0].category}` : "none seen",
			accent: "text-default"
		}
	]
})

const byCount = <T extends { count: number }>(rows: T[]) => [...rows].sort((a, b) => b.count - a.count)

const categories = computed<WafRankItem[]>(() =>
	byCount(stats.value?.attack_categories ?? []).map(c => ({ key: c.category, label: c.category, value: c.count }))
)
const countries = computed<WafRankItem[]>(() =>
	byCount(stats.value?.top_countries ?? []).map(c => ({
		key: c.country_code ?? c.country_name ?? "unknown",
		label: c.country_name ?? c.country_code ?? "Unknown",
		value: c.count,
		code: c.country_code
	}))
)
const rules = computed<WafRankItem[]>(() =>
	byCount(stats.value?.top_rules ?? []).map(r => ({ key: r.rule_id ?? "none", label: r.rule_id ?? "—", value: r.count }))
)
const ips = computed<WafRankItem[]>(() =>
	byCount(stats.value?.top_ips ?? []).map(i => ({ key: i.client_ip, label: i.client_ip, value: i.count }))
)

function formatLag(seconds: number) {
	if (seconds < 60) return `${seconds.toFixed(1)}s`
	if (seconds < 3600) return `${Math.round(seconds / 60)}m`
	return `${(seconds / 3600).toFixed(1)}h`
}

function openBlock(ip: string) {
	blockTarget.value = ip
	showBlock.value = true
}

onBeforeMount(() => {
	loading.value = true
	Api.customerWaf
		.getStats(customerCode, instance.id)
		.then(res => {
			stats.value = res.data.stats
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
})
</script>
