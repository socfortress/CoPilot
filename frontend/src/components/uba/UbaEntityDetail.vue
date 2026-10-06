<template>
	<div class="flex flex-col gap-6" data-testid="uba-entity-detail">
		<UbaError v-if="error" :error />
		<n-spin v-else :show="loading" class="min-h-40">
			<div v-if="detail" class="flex flex-col gap-7">
				<UbaSection title="Risk over time" test-id="uba-entity-history">
					<template #actions>
						<SegmentedToggle
							v-model="range"
							:options="RANGES.map(r => ({ value: r.value, label: r.value }))"
							label="Range"
							test-id="uba-risk-range"
						/>
					</template>
					<UbaError v-if="historyError" :error="historyError" />
					<n-spin v-else :show="historyLoading">
						<UbaRiskChart v-if="history" :history />
						<div v-else class="h-[200px]" />
					</n-spin>
				</UbaSection>

				<UbaSection title="Risk by rule" caption="last 14 days, decayed to now" test-id="uba-entity-rules">
					<ul class="border-default m-0 flex list-none flex-col overflow-hidden rounded-lg border p-0">
						<li
							v-for="part of detail.risk_by_rule"
							:key="part.rule_id"
							class="rule-row border-default flex items-center gap-3 border-b px-3 py-2 last:border-b-0"
							data-testid="uba-rule-row"
						>
							<span class="w-11 shrink-0 text-right font-mono text-sm font-semibold tabular-nums">
								{{ riskLabel(part.risk) }}
							</span>
							<!-- This rule's share of the entity's risk now. -->
							<span class="share-track relative h-1 w-16 shrink-0 overflow-hidden rounded-full">
								<span
									class="bg-primary absolute inset-y-0 left-0 rounded-full"
									:style="{ width: `${share(part.risk)}%` }"
								/>
							</span>
							<span class="min-w-0 flex-1 truncate font-mono text-xs">{{ part.rule_id }}</span>
							<n-tag v-if="part.native" size="tiny" :bordered="false">native</n-tag>
							<span class="text-tertiary w-7 font-mono text-[11px] tabular-nums">
								×{{ part.signals }}
							</span>
							<div class="flex min-w-22 items-center gap-1">
								<n-tag v-if="isSuppressed(part.rule_id)" size="tiny" type="success" :bordered="false">
									suppressed
								</n-tag>
								<n-button
									v-else
									size="tiny"
									quaternary
									:loading="suppressing === part.rule_id"
									:aria-label="`Suppress ${part.rule_id} for this entity`"
									@click="suppress(part.rule_id)"
								>
									<template #icon><Icon name="carbon:notification-off" :size="13" /></template>
									Suppress
								</n-button>
							</div>
						</li>
						<li v-if="!detail.risk_by_rule.length" class="text-secondary px-3 py-3 text-sm">
							No risk in the last 14 days.
						</li>
					</ul>
				</UbaSection>

				<UbaSection
					v-if="detail.alerts.length"
					title="Alerts"
					:caption="`${detail.alerts.length}`"
					test-id="uba-entity-alerts"
				>
					<ul class="m-0 flex list-none flex-col gap-1.5 p-0">
						<li
							v-for="a of detail.alerts"
							:key="a.id"
							class="alert-row border-default flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border px-3 py-2"
							role="button"
							tabindex="0"
							:aria-label="`Open the UBA alert of ${formatDate(a.opened_at, dFormats.datetime)}`"
							data-testid="uba-entity-alert"
							@click="emit('openAlert', a.id)"
							@keydown.enter.prevent="emit('openAlert', a.id)"
							@keydown.space.prevent="emit('openAlert', a.id)"
						>
							<RiskMeter :risk="a.risk" :threshold />
							<span class="font-mono text-xs tabular-nums">{{ formatDate(a.opened_at, dFormats.datetime) }}</span>
							<n-tag
								size="tiny"
								:type="!a.verdict ? 'error' : a.verdict === 'FALSE_POSITIVE' ? 'default' : 'error'"
								:bordered="false"
							>
								{{ !a.verdict ? "open" : a.verdict === "FALSE_POSITIVE" ? "false positive" : "true positive" }}
							</n-tag>
							<span class="ml-auto flex items-center gap-2">
								<n-button
									v-if="a.copilot_alert_id"
									size="tiny"
									quaternary
									@click.stop="routeIncidentManagementAlerts(a.copilot_alert_id).navigate()"
									@keydown.enter.stop
								>
									Incident #{{ a.copilot_alert_id }}
								</n-button>
								<Icon name="carbon:arrow-right" :size="14" class="go text-tertiary" aria-hidden="true" />
							</span>
						</li>
					</ul>
				</UbaSection>

				<UbaSection v-if="detail.host" title="Computer" test-id="uba-entity-host">
					<ul class="kv border-default m-0 list-none overflow-hidden rounded-lg border p-0 text-sm">
						<li>
							<span class="k">Name</span>
							<span class="v">{{ detail.host.name }}</span>
						</li>
						<li>
							<span class="k">System</span>
							<span class="v">
								{{ detail.host.os || detail.host.platform || "unknown" }}
								<span v-if="detail.host.role" class="text-tertiary text-xs">· {{ detail.host.role }}</span>
							</span>
						</li>
						<li v-if="detail.host.ip">
							<span class="k">Address</span>
							<span class="v font-mono text-xs">{{ detail.host.ip }}</span>
						</li>
						<li>
							<span class="k">Wazuh agent</span>
							<span class="v">
								<span class="font-mono text-xs">{{ detail.host.agent_id }}</span>
								<span v-if="detail.host.agent_version" class="text-tertiary text-xs">· {{ detail.host.agent_version }}</span>
								<span v-if="detail.host.groups.length" class="text-tertiary text-xs">
									· groups {{ detail.host.groups.join(", ") }}
								</span>
							</span>
						</li>
						<li>
							<span class="k">Reporting</span>
							<span class="v">
								{{ REPORTING_LABELS[detail.host.reporting] }}
								<span v-if="detail.host.last_keepalive" class="text-tertiary text-xs">
									· last check-in {{ formatDate(detail.host.last_keepalive, dFormats.datetime) }}
								</span>
							</span>
						</li>
						<li v-if="detail.host.registered_at">
							<span class="k">Enrolled</span>
							<span class="v">{{ formatDate(detail.host.registered_at, dFormats.date) }}</span>
						</li>
					</ul>
				</UbaSection>

				<UbaSection v-if="detail.identity" title="Identity" test-id="uba-entity-identity">
					<template #actions>
						<n-tag size="tiny" :bordered="false" round>{{ detail.identity.kind || "unknown" }}</n-tag>
						<n-tag v-if="detail.identity.shadow" size="tiny" :bordered="false" round>
							<template #icon><Icon name="carbon:data-enrichment" :size="11" /></template>
							learned from events
						</n-tag>
					</template>
					<ul class="kv border-default m-0 list-none overflow-hidden rounded-lg border p-0 text-sm">
						<li v-if="accountState">
							<span class="k">Account</span>
							<span class="v flex flex-wrap items-center gap-2">
								<n-tag size="tiny" :type="accountState.type" :bordered="false">{{ accountState.label }}</n-tag>
								<span v-if="detail.identity.account_created_at" class="text-tertiary text-xs">
									created {{ formatDate(detail.identity.account_created_at, dFormats.date) }}
								</span>
								<span v-if="detail.identity.attr_source?.enabled" class="text-tertiary text-xs">
									· {{ identitySourceLabel(detail.identity.attr_source.enabled) }}
								</span>
							</span>
						</li>
						<li v-if="detail.identity.privileged_reasons.length">
							<span class="k">Privileged</span>
							<span class="v flex flex-col gap-1">
								<span v-for="r of detail.identity.privileged_reasons" :key="r" class="flex flex-wrap items-baseline gap-x-2">
									<span class="flex items-center gap-1.5">
										<Icon name="carbon:security" :size="13" class="text-warning" />
										{{ privilegedReasonLabel(r).what }}
									</span>
									<span class="text-tertiary text-xs">{{ privilegedReasonLabel(r).how }}</span>
								</span>
							</span>
						</li>
						<li v-if="detail.identity.memberships?.length">
							<span class="k">Groups</span>
							<span class="v flex flex-col gap-1">
								<span
									v-for="m of detail.identity.memberships"
									:key="`${m.source}:${m.group_name}`"
									class="flex flex-wrap items-center gap-x-2 gap-y-0.5"
								>
									{{ m.group_name }}
									<n-tag v-if="m.privileged" size="tiny" type="warning" :bordered="false">admin</n-tag>
									<span class="text-tertiary text-xs">
										{{ identitySourceLabel(m.source) }}{{ m.since ? ` · since ${formatDate(m.since, dFormats.date)}` : "" }}
									</span>
								</span>
							</span>
						</li>
						<li v-if="detail.identity.aliases.length">
							<span class="k">Aliases</span>
							<!-- One grid for all aliases: kinds in one column, values in the next, on one baseline. -->
							<span
								class="v grid grid-cols-[max-content_minmax(0,1fr)] items-baseline gap-x-3 gap-y-1.5"
								data-testid="uba-identity-aliases"
							>
								<template v-for="a of detail.identity.aliases" :key="`${a.type}:${a.value}`">
									<span class="alias-type justify-self-start font-mono text-[11px]" data-testid="uba-identity-alias">
										{{ a.type }}
									</span>
									<span class="alias-value truncate font-mono text-xs" :title="a.value">{{ a.value }}</span>
								</template>
							</span>
						</li>
					</ul>
				</UbaSection>

				<UbaSection
					title="Timeline"
					:caption="`${timelineTotal} finding${timelineTotal === 1 ? '' : 's'}`"
					test-id="uba-entity-timeline"
				>
					<SignalTimeline :items="timelineItems" :customer-code />
					<n-button
						v-if="timeline.length < timelineTotal"
						size="small"
						secondary
						:loading="loadingMore"
						class="self-start"
						@click="loadMore"
					>
						Load more
					</n-button>
				</UbaSection>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { SignalTimelineItem } from "./ui/SignalTimeline.vue"
import type { UbaDrawerMeta } from "./ui/UbaDrawerHeader.vue"
import type { ApiError } from "@/types/common"
import type { UbaEntityDetail, UbaReportingState, UbaRiskHistory, UbaRiskStep, UbaSignal } from "@/types/uba"
import { NButton, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaRiskChart from "./UbaRiskChart.vue"
import RiskMeter from "./ui/RiskMeter.vue"
import SignalTimeline from "./ui/SignalTimeline.vue"
import UbaSection from "./ui/UbaSection.vue"
import { entityTypeIcon, entityTypeLabel, identitySourceLabel, privilegedReasonLabel, riskLabel } from "./utils"

const { customerCode, entityKey } = defineProps<{ customerCode: string; entityKey: string }>()
const emit = defineEmits<{ openAlert: [alertId: string]; changed: []; meta: [meta: UbaDrawerMeta] }>()
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
	if (identity.deleted_at)
		return { label: `deleted ${formatDate(identity.deleted_at, dFormats.date)}`, type: "error" }
	if (identity.enabled === false) return { label: "account disabled", type: "warning" }
	if (identity.enabled === true) return { label: "account enabled", type: "success" }
	return null
})

/** The customer's alert threshold, from the risk history (100 until it loads). */
const threshold = computed(() => history.value?.alert_threshold ?? 100)

/** A rule's share of the entity's risk now, as a percent of its strongest rule's: the bars compare rules. */
function share(risk: number) {
	const top = Math.max(...(detail.value?.risk_by_rule.map(p => p.risk) ?? [0]), 0)
	return top ? Math.max(4, (risk / top) * 100) : 0
}

const timelineItems = computed<SignalTimelineItem[]>(() =>
	timeline.value.map(s => ({
		key: s.id,
		time: s.time,
		ruleId: s.rule_id,
		explanation: s.explanation,
		points: s.effective_score,
		native: s.native,
		suppressed: s.suppressed,
		muted: s.suppressed || s.effective_score === 0,
		signalId: s.id,
		evidenceCount: s.evidence.length
	}))
)

/** What the drawer's header shows: the entity's name, type, key and risk, and what qualifies it. */
const meta = computed<UbaDrawerMeta | null>(() => {
	const d = detail.value
	if (!d) return null
	const tags: NonNullable<UbaDrawerMeta["tags"]> = []
	if (d.identity?.privileged) tags.push({ label: "privileged", type: "warning", icon: "carbon:security" })
	if (d.host && d.host.reporting !== "reporting")
		tags.push({ label: REPORTING_LABELS[d.host.reporting], type: "warning" })
	const open = d.alerts.find(a => !a.verdict)
	if (open) tags.push({ label: "open alert", type: "error", icon: "carbon:warning-alt-filled" })
	if (d.suppressions.some(s => s.active)) tags.push({ label: "suppressions", icon: "carbon:notification-off" })
	return {
		kind: `Entity · ${entityTypeLabel(d.entity_type)}`,
		icon: entityTypeIcon(d.entity_type),
		title: d.entity_name || d.entity_key,
		key: d.entity_key,
		keyLabel: "Entity key",
		risk: d.risk,
		threshold: threshold.value,
		tags
	}
})

watch(meta, value => value && emit("meta", value))

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

<style scoped>
/* Key/value rows: a fixed column of quiet mono keys, values beside them, hairlines between. */
.kv li {
	display: grid;
	grid-template-columns: 112px minmax(0, 1fr);
	gap: 12px;
	align-items: baseline;
	padding: 8px 12px;
	border-bottom: 1px solid var(--border-color);
}

.kv li:last-child {
	border-bottom: 0;
}

.kv .k {
	font-family: var(--font-family-mono);
	font-size: 11px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--fg-tertiary-color);
}

.kv .v {
	min-width: 0;
}

.alias-type {
	padding: 1px 6px;
	border-radius: 4px;
	line-height: 1.4;
	color: var(--fg-secondary-color);
	background-color: var(--hover-color);
}

.alias-value {
	color: var(--fg-default-color);
}

.share-track {
	background-color: var(--hover-color);
}

.rule-row:hover,
.alert-row:hover {
	background-color: var(--hover-005-color);
}

.alert-row {
	transition:
		border-color 0.15s,
		background-color 0.15s;
}

.alert-row:hover,
.alert-row:focus-visible {
	border-color: var(--primary-color);
	outline: none;
}

.alert-row:hover .go,
.alert-row:focus-visible .go {
	color: var(--primary-color);
}
</style>
