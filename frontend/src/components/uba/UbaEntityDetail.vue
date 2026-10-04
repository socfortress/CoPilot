<template>
	<div class="flex flex-col gap-4">
		<UbaError v-if="error" :error />
		<n-spin v-else :show="loading" class="min-h-40">
			<template v-if="detail">
				<header class="flex flex-wrap items-center gap-2">
					<n-tag :type="riskTagType(detail.risk)" round :bordered="false">risk {{ riskLabel(detail.risk) }}</n-tag>
					<n-tag size="small" :bordered="false">{{ entityTypeLabel(detail.entity_type) }}</n-tag>
					<n-tag v-if="detail.identity?.privileged" size="small" type="warning" :bordered="false">privileged</n-tag>
					<n-tag v-if="detail.host && detail.host.reporting !== 'reporting'" size="small" type="warning" :bordered="false">
						{{ REPORTING_LABELS[detail.host.reporting] }}
					</n-tag>
					<span class="text-tertiary font-mono text-xs">{{ detail.entity_key }}</span>
				</header>

				<section class="flex flex-col gap-2">
					<div class="flex flex-wrap items-center justify-between gap-2">
						<span :class="SECTION_LABEL">Risk over time</span>
						<n-radio-group v-model:value="range" size="small">
							<n-radio-button v-for="r of RANGES" :key="r.value" :value="r.value">{{ r.value }}</n-radio-button>
						</n-radio-group>
					</div>
					<UbaError v-if="historyError" :error="historyError" />
					<n-spin v-else :show="historyLoading">
						<UbaRiskChart v-if="history" :history />
						<div v-else class="h-[200px]" />
					</n-spin>
				</section>

				<section class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Risk by rule (last 14 days, decayed now)</span>
					<ul class="divide-border border-default flex flex-col divide-y rounded-lg border">
						<li v-for="part of detail.risk_by_rule" :key="part.rule_id" class="flex items-center gap-3 px-3 py-2">
							<span class="w-14 text-right font-mono text-sm">{{ riskLabel(part.risk) }}</span>
							<span class="min-w-0 flex-1 truncate font-mono text-xs">{{ part.rule_id }}</span>
							<n-tag v-if="part.native" size="tiny" :bordered="false">native</n-tag>
							<span class="text-tertiary text-xs">×{{ part.signals }}</span>
							<n-button
								v-if="!isSuppressed(part.rule_id)"
								size="tiny"
								secondary
								:loading="suppressing === part.rule_id"
								@click="suppress(part.rule_id)"
							>
								Suppress
							</n-button>
							<n-tag v-else size="tiny" type="success" :bordered="false">suppressed</n-tag>
						</li>
						<li v-if="!detail.risk_by_rule.length" class="text-secondary px-3 py-2 text-sm">No risk in the last 14 days.</li>
					</ul>
				</section>

				<section v-if="detail.host" class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Computer</span>
					<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
						<dt class="text-secondary">Name</dt>
						<dd>{{ detail.host.name }}</dd>
						<dt class="text-secondary">System</dt>
						<dd>{{ detail.host.os || detail.host.platform || "unknown" }}{{ detail.host.role ? ` (${detail.host.role})` : "" }}</dd>
						<template v-if="detail.host.ip">
							<dt class="text-secondary">Address</dt>
							<dd class="font-mono text-xs">{{ detail.host.ip }}</dd>
						</template>
						<dt class="text-secondary">Wazuh agent</dt>
						<dd>
							{{ detail.host.agent_id }}{{ detail.host.agent_version ? ` · ${detail.host.agent_version}` : "" }}{{
								detail.host.groups.length ? ` · groups ${detail.host.groups.join(", ")}` : ""
							}}
						</dd>
						<dt class="text-secondary">Reporting</dt>
						<dd>
							{{ REPORTING_LABELS[detail.host.reporting] }}{{
								detail.host.last_keepalive ? ` · last check-in ${formatDate(detail.host.last_keepalive, dFormats.datetime)}` : ""
							}}
						</dd>
						<template v-if="detail.host.registered_at">
							<dt class="text-secondary">Enrolled</dt>
							<dd>{{ formatDate(detail.host.registered_at, dFormats.date) }}</dd>
						</template>
					</dl>
				</section>

				<section v-if="detail.identity" class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Identity</span>
					<div v-if="accountState" class="flex flex-wrap items-center gap-2 text-sm">
						<n-tag size="small" :type="accountState.type" :bordered="false">{{ accountState.label }}</n-tag>
						<span v-if="detail.identity.account_created_at" class="text-secondary text-xs">
							created in the directory {{ formatDate(detail.identity.account_created_at, dFormats.date) }}
						</span>
						<span v-if="detail.identity.attr_source?.enabled" class="text-tertiary text-xs">
							· from {{ identitySourceLabel(detail.identity.attr_source.enabled) }}
						</span>
					</div>
					<div v-if="detail.identity.privileged_reasons.length" class="flex flex-col gap-1">
						<span class="text-secondary text-xs">Privileged because</span>
						<ul class="flex flex-col gap-0.5">
							<li v-for="r of detail.identity.privileged_reasons" :key="r" class="text-sm">
								<b>{{ privilegedReasonLabel(r).what }}</b>
								<span class="text-tertiary text-xs">· {{ privilegedReasonLabel(r).how }}</span>
							</li>
						</ul>
					</div>
					<div v-if="detail.identity.memberships?.length" class="flex flex-col gap-1">
						<span class="text-secondary text-xs">Roles and groups</span>
						<ul class="flex flex-col gap-0.5">
							<li
								v-for="m of detail.identity.memberships"
								:key="`${m.source}:${m.group_name}`"
								class="flex flex-wrap items-center gap-2 text-sm"
							>
								<span>{{ m.group_name }}</span>
								<n-tag v-if="m.privileged" size="tiny" type="warning" :bordered="false">admin</n-tag>
								<span class="text-tertiary text-xs">
									{{ identitySourceLabel(m.source) }}{{ m.since ? ` · since ${formatDate(m.since, dFormats.date)}` : "" }}
								</span>
							</li>
						</ul>
					</div>
					<div class="flex flex-wrap gap-1.5">
						<span
							v-for="a of detail.identity.aliases"
							:key="`${a.type}:${a.value}`"
							class="border-default bg-secondary rounded-md border px-2 py-0.5 font-mono text-xs"
						>
							{{ a.type }}: {{ a.value }}
						</span>
					</div>
					<span class="text-tertiary text-xs">
						{{ detail.identity.kind || "unknown" }}{{ detail.identity.shadow ? " · learned from events" : "" }}
					</span>
				</section>

				<section v-if="detail.alerts.length" class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Alerts</span>
					<ul class="flex flex-col gap-1">
						<li v-for="a of detail.alerts" :key="a.id" class="flex flex-wrap items-center gap-2">
							<n-button text type="primary" size="small" @click="emit('openAlert', a.id)">
								{{ formatDate(a.opened_at, dFormats.datetime) }} · risk {{ riskLabel(a.risk) }}
								{{ a.verdict ? `· ${a.verdict === "FALSE_POSITIVE" ? "false positive" : "true positive"}` : "" }}
							</n-button>
							<n-button
								v-if="a.copilot_alert_id"
								text
								size="small"
								class="text-secondary"
								@click="routeIncidentManagementAlerts(a.copilot_alert_id).navigate()"
							>
								incident alert #{{ a.copilot_alert_id }}
							</n-button>
						</li>
					</ul>
				</section>

				<section class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Timeline ({{ timelineTotal }} signals)</span>
					<ul class="flex flex-col gap-2">
						<li
							v-for="s of timeline"
							:key="s.id"
							class="border-default rounded-lg border px-3 py-2"
							:class="{ 'opacity-60': s.suppressed || s.effective_score === 0 }"
						>
							<div class="flex flex-wrap items-center gap-2">
								<span class="text-tertiary text-xs">{{ formatDate(s.time, dFormats.datetime) }}</span>
								<span class="font-mono text-xs">{{ s.rule_id }}</span>
								<n-tag v-if="s.native" size="tiny" :bordered="false">native</n-tag>
								<n-tag v-if="s.suppressed" size="tiny" type="success" :bordered="false">suppressed</n-tag>
								<span class="text-tertiary ml-auto text-xs">+{{ riskLabel(s.effective_score) }}</span>
							</div>
							<p class="mt-1 text-sm">{{ s.explanation }}</p>
							<UbaEvidence :customer-code :signal-id="s.id" :count="s.evidence.length" class="mt-1" />
						</li>
					</ul>
					<n-button v-if="timeline.length < timelineTotal" size="small" secondary :loading="loadingMore" @click="loadMore">
						Load more
					</n-button>
				</section>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaEntityDetail, UbaReportingState, UbaRiskHistory, UbaRiskStep, UbaSignal } from "@/types/uba"
import { NButton, NRadioButton, NRadioGroup, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaEvidence from "./UbaEvidence.vue"
import UbaRiskChart from "./UbaRiskChart.vue"
import { entityTypeLabel, identitySourceLabel, privilegedReasonLabel, riskLabel, riskTagType } from "./utils"

const { customerCode, entityKey } = defineProps<{ customerCode: string; entityKey: string }>()
const emit = defineEmits<{ openAlert: [alertId: string]; changed: [] }>()
const REPORTING_LABELS: Record<UbaReportingState, string> = {
	reporting: "reporting",
	not_reporting: "not reporting",
	retired: "retired (silent over 30 days)",
	never_connected: "never connected"
}
const PAGE_SIZE = 30
const { routeIncidentManagementAlerts } = useNavigation()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const loadingMore = ref(false)
const suppressing = ref<string | null>(null)
const error = ref<ApiError | null>(null)
const detail = ref<UbaEntityDetail | null>(null)
const timeline = ref<UbaSignal[]>([])
const timelineTotal = ref(0)
const timelinePage = ref(1)

// Risk over time: the range picks the step so the chart stays a few hundred points.
const RANGES: { value: string; step: UbaRiskStep }[] = [
	{ value: "24h", step: "15m" },
	{ value: "7d", step: "1h" },
	{ value: "14d", step: "1h" },
	{ value: "30d", step: "6h" }
]
const range = ref("14d")
const history = ref<UbaRiskHistory | null>(null)
const historyLoading = ref(false)
const historyError = ref<ApiError | null>(null)

function loadHistory() {
	const step = RANGES.find(r => r.value === range.value)?.step ?? "1h"
	historyLoading.value = true
	historyError.value = null
	Api.uba
		.getEntityRiskHistory(customerCode, entityKey, range.value, step)
		.then(res => {
			history.value = res.data
		})
		.catch((err: ApiError) => {
			historyError.value = err
		})
		.finally(() => {
			historyLoading.value = false
		})
}

watch(range, loadHistory)

// The directory's view of the account, when any source told UBA (sync or account-change events).
const accountState = computed<{ label: string; type: "success" | "warning" | "error" } | null>(() => {
	const identity = detail.value?.identity
	if (!identity) return null
	if (identity.deleted_at) return { label: `deleted ${formatDate(identity.deleted_at, dFormats.date)}`, type: "error" }
	if (identity.enabled === false) return { label: "account disabled", type: "warning" }
	if (identity.enabled === true) return { label: "account enabled", type: "success" }
	return null
})

function isSuppressed(ruleId: string) {
	return detail.value?.suppressions.some(s => s.rule_id === ruleId && s.active) ?? false
}

function load() {
	loading.value = true
	error.value = null
	timelinePage.value = 1
	Promise.all([
		Api.uba.getEntity(customerCode, entityKey),
		Api.uba.getEntityTimeline(customerCode, entityKey, 1, PAGE_SIZE)
	])
		.then(([entity, signals]) => {
			detail.value = entity.data
			timeline.value = signals.data.signals
			timelineTotal.value = signals.data.total
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function loadMore() {
	loadingMore.value = true
	Api.uba
		.getEntityTimeline(customerCode, entityKey, timelinePage.value + 1, PAGE_SIZE)
		.then(res => {
			timelinePage.value += 1
			timeline.value = [...timeline.value, ...res.data.signals]
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Loading the timeline failed.")
		})
		.finally(() => {
			loadingMore.value = false
		})
}

function suppress(ruleId: string) {
	suppressing.value = ruleId
	Api.uba
		.addSuppressions(customerCode, { entity_key: entityKey, rule_ids: [ruleId], days: 30 })
		.then(() => {
			message.success(`${ruleId} no longer adds risk for this entity for 30 days.`)
			emit("changed")
			load()
			loadHistory() // a suppressed rule no longer adds risk
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Suppressing failed.")
		})
		.finally(() => {
			suppressing.value = null
		})
}

onBeforeMount(() => {
	load()
	loadHistory()
})
</script>
