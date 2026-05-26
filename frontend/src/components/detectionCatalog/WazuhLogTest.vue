<template>
	<div class="flex flex-col gap-3">
		<p class="text-sm">Paste a raw log, see which Wazuh rule would fire (via Wazuh logtest)</p>

		<div class="flex flex-col gap-3">
			<div v-if="history.length" class="flex flex-wrap items-center gap-2">
				<span class="text-tertiary text-xs">Recent:</span>
				<button
					v-for="(item, idx) of history"
					:key="idx"
					type="button"
					class="history-chip"
					:title="item.event"
					@click="restoreFromHistory(item)"
				>
					<span v-if="item.matched" class="history-rule-id">{{ item.rule_id ?? "?" }}</span>
					<span v-else class="text-tertiary text-xs">no match</span>
					<span class="history-preview">{{ truncate(item.event, 28) }}</span>
				</button>
				<button type="button" class="history-clear" @click="clearHistory">Clear</button>
			</div>

			<n-input
				v-model:value="event"
				type="textarea"
				placeholder="Paste a single log line — auditd / syslog / Windows EventChannel / Suricata eve.json etc."
				:autosize="{ minRows: 3, maxRows: 8 }"
			/>

			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="flex items-center gap-2">
					<span class="text-tertiary text-xs">Format</span>
					<n-select
						v-model:value="logFormat"
						:options="logFormatOptions"
						size="small"
						style="min-width: 180px"
					/>
				</div>

				<div class="flex items-center gap-2">
					<n-button v-if="result" size="small" quaternary @click="clearResult">Clear result</n-button>
					<n-button type="primary" size="small" :loading="testing" :disabled="!event.trim()" @click="runTest">
						<template #icon><Icon name="carbon:play-filled-alt" /></template>
						Test against Wazuh
					</n-button>
				</div>
			</div>

			<!-- RESULT --------------------------------------------------- -->
			<template v-if="result">
				<n-alert v-if="result.unavailable_reason" type="error" show-icon>
					<template #header>Logtest failed</template>
					{{ result.unavailable_reason }}
				</n-alert>

				<CardEntity v-else-if="!result.matched" size="small" status="warning">
					<template #default>
						<div class="flex items-start gap-3">
							<Icon name="carbon:information" :size="18" class="text-warning mt-0.5" />
							<div class="flex flex-col gap-1">
								<div class="text-sm font-semibold">No rule matched</div>
								<div class="text-secondary text-xs leading-relaxed">
									Wazuh saw the log but no analyst-facing rule fired. Try a different "Format" — most
									agent-forwarded logs use
									<code>syslog</code>
									; pure JSON payloads use
									<code>json</code>
									.
								</div>
							</div>
						</div>
					</template>
				</CardEntity>

				<CardEntity v-else-if="result.rule" size="small" status="success">
					<template #header>
						<div class="flex flex-wrap items-center justify-between gap-2">
							<div class="flex items-center gap-2">
								<Icon name="carbon:checkmark-filled" :size="16" class="text-success" />
								<span class="text-sm font-semibold tracking-wide uppercase">Match</span>
								<Badge type="splitted" color="success">
									<template #label>Rule</template>
									<template #value>{{ result.rule.id }}</template>
								</Badge>
								<Badge type="splitted" :color="levelBadgeColor(result.rule.level)">
									<template #label>Level</template>
									<template #value>{{ result.rule.level ?? "—" }}</template>
								</Badge>
							</div>
							<n-button
								v-if="result.rule.id !== null"
								size="tiny"
								secondary
								@click="emit('open-rule', result.rule.id!)"
							>
								<template #icon><Icon name="carbon:arrow-right" /></template>
								View in catalog
							</n-button>
						</div>
					</template>

					<template #default>
						<div class="flex flex-col gap-3">
							<div class="text-secondary text-sm leading-relaxed">
								{{ result.rule.description }}
							</div>
							<div
								v-if="result.rule.groups.length || result.rule.mitre.length || result.tactics.length"
								class="flex flex-wrap gap-1.5"
							>
								<span
									v-for="g of result.rule.groups"
									:key="`g-${g}`"
									class="match-pill match-pill-group"
								>
									{{ g }}
								</span>
								<span
									v-for="t of result.rule.mitre"
									:key="`m-${t}`"
									class="match-pill match-pill-mitre"
								>
									{{ t }}
								</span>
								<span v-for="t of result.tactics" :key="`t-${t}`" class="match-pill match-pill-tactic">
									{{ t.toUpperCase() }}
								</span>
							</div>
						</div>
					</template>
				</CardEntity>

				<!-- Decoded alert envelope, optional collapsible block. -->
				<n-collapse v-if="result.alert" arrow-placement="right">
					<n-collapse-item title="Decoded alert envelope" name="alert">
						<pre class="alert-envelope"><code>{{ formatAlert(result.alert) }}</code></pre>
					</n-collapse-item>
				</n-collapse>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CatalogLogTestResponse } from "@/types/detectionCatalog.d"
import { NAlert, NButton, NCollapse, NCollapseItem, NInput, NSelect, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{ (e: "open-rule", ruleId: number): void }>()
const HISTORY_STORAGE_KEY = "detectionCatalog.logtest.history"
const HISTORY_MAX = 5

interface LogTestHistoryItem {
	event: string
	log_format: string
	matched: boolean
	rule_id: number | null
	rule_description: string
	timestamp: string
}

const message = useMessage()

const event = ref("")
const logFormat = ref("syslog")

// Wazuh's most common log formats. Covers ~95% of analyst pastes — full list
// would have ~30 entries and feel overwhelming for a one-off test.
const logFormatOptions = [
	{ label: "syslog", value: "syslog" },
	{ label: "json", value: "json" },
	{ label: "snort-full", value: "snort-full" },
	{ label: "squid", value: "squid" },
	{ label: "apache", value: "apache" },
	{ label: "iis", value: "iis" },
	{ label: "audit", value: "audit" },
	{ label: "djb-multilog", value: "djb-multilog" },
	{ label: "eventlog (Windows EVT)", value: "eventlog" },
	{ label: "eventchannel (Windows EventChannel)", value: "eventchannel" }
]

const testing = ref(false)
const result = ref<CatalogLogTestResponse | null>(null)
const history = ref<LogTestHistoryItem[]>([])

function clearResult() {
	result.value = null
}

function loadHistory() {
	try {
		const raw = localStorage.getItem(HISTORY_STORAGE_KEY)
		if (!raw) return
		const parsed = JSON.parse(raw)
		if (Array.isArray(parsed)) {
			history.value = parsed
				.filter(item => typeof item?.event === "string" && typeof item?.log_format === "string")
				.slice(0, HISTORY_MAX)
		}
	} catch {
		/* localStorage corrupted or disabled — start fresh, non-fatal. */
	}
}

function persistHistory() {
	try {
		localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history.value))
	} catch {
		/* QuotaExceeded / disabled — history is best-effort. */
	}
}

function recordInHistory(res: CatalogLogTestResponse) {
	const item: LogTestHistoryItem = {
		event: event.value,
		log_format: logFormat.value,
		matched: res.matched,
		rule_id: res.rule?.id ?? null,
		rule_description: res.rule?.description ?? "",
		timestamp: new Date().toISOString()
	}
	// De-dupe consecutive identical pastes.
	const dup = history.value[0]
	if (dup && dup.event === item.event && dup.log_format === item.log_format) {
		history.value[0] = item
	} else {
		history.value = [item, ...history.value].slice(0, HISTORY_MAX)
	}
	persistHistory()
}

function restoreFromHistory(item: LogTestHistoryItem) {
	event.value = item.event
	logFormat.value = item.log_format
	result.value = null
}

function clearHistory() {
	history.value = []
	persistHistory()
}

function truncate(s: string, n: number): string {
	if (s.length <= n) return s
	return `${s.slice(0, n - 1)}…`
}

function runTest() {
	if (!event.value.trim()) return
	testing.value = true
	Api.detectionCatalog
		.runLogTest({
			event: event.value,
			log_format: logFormat.value,
			location: "logtest"
		})
		.then(res => {
			if (res.data?.success) {
				result.value = res.data
				recordInHistory(res.data)
			} else {
				message.warning(res.data?.message || "Logtest returned an unexpected response")
			}
		})
		.catch(err => {
			const detail = err.response?.data?.detail || err.response?.data?.message
			message.error(detail || "Logtest request failed")
		})
		.finally(() => {
			testing.value = false
		})
}

function levelBadgeColor(level: number | null): "danger" | "warning" | "primary" | "success" | undefined {
	if (level === null || level === undefined) return undefined
	if (level >= 12) return "danger"
	if (level >= 7) return "warning"
	if (level >= 3) return "primary"
	return "success"
}

function formatAlert(alert: Record<string, unknown>): string {
	try {
		return JSON.stringify(alert, null, 2)
	} catch {
		return String(alert)
	}
}

onBeforeMount(loadHistory)
</script>

<style scoped lang="scss">
.history-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 3px 8px;
	font-size: 0.7rem;
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 999px;
	cursor: pointer;
	transition: all 0.15s var(--bezier-ease);

	&:hover {
		border-color: rgba(var(--primary-color-rgb) / 0.4);
		background-color: rgba(var(--primary-color-rgb) / 0.05);
	}
}

.history-rule-id {
	font-family: var(--font-family-mono);
	font-weight: 600;
	color: var(--primary-color);
}

.history-preview {
	max-width: 200px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--fg-secondary-color);
	font-family: var(--font-family-mono);
}

.history-clear {
	background: transparent;
	border: none;
	color: var(--fg-secondary-color);
	font-size: 0.7rem;
	cursor: pointer;
	padding: 3px 6px;

	&:hover {
		color: var(--fg-default-color);
		text-decoration: underline;
	}
}

/* Match-card chips - mirror the modal's groups/mitre/tactic pills so the
   logtest result feels like a preview of the catalog modal. */
.match-pill {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	font-size: 0.7rem;
	font-weight: 500;
	border-radius: 999px;
	border: 1px solid transparent;
}
.match-pill-group {
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.08);
	border-color: rgba(var(--primary-color-rgb) / 0.18);
}
.match-pill-mitre {
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
	font-family: var(--font-family-mono);
}
.match-pill-tactic {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.1);
	border-color: rgba(var(--warning-color-rgb) / 0.25);
	font-weight: 600;
	letter-spacing: 0.04em;
}

.alert-envelope {
	margin: 0;
	padding: 10px 12px;
	max-height: 300px;
	overflow: auto;
	font-family: var(--font-family-mono);
	font-size: 0.72rem;
	line-height: 1.45;
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px;
	white-space: pre;
}
.alert-envelope code {
	display: block;
}
</style>
