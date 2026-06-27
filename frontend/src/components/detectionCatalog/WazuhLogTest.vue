<template>
	<div class="flex flex-col gap-6">
		<div class="flex flex-col gap-2">
			<p>Paste a raw log, see which Wazuh rule would fire (via Wazuh logtest)</p>

			<div v-if="history.length" class="flex justify-end">
				<n-popover placement="left-start" class="p-3!">
					<template #trigger>
						<div class="text-secondary flex items-center gap-2 text-xs">
							<Icon name="carbon:time" />
							History
						</div>
					</template>

					<div class="flex flex-col gap-4">
						<n-scrollbar trigger="none" class="max-h-50">
							<div class="flex flex-col gap-2">
								<Badge
									v-for="(item, idx) of history"
									:key="idx"
									point-cursor
									type="splitted"
									@click="restoreFromHistory(item)"
								>
									<template #label>
										<span
											v-if="item.matched"
											class="text-primary max-w-20 truncate font-mono text-xs"
											:title="item.rule_id?.toString() ?? '?'"
										>
											{{ item.rule_id ?? "?" }}
										</span>
										<span v-else class="text-tertiary font-mono text-xs">no match</span>
									</template>
									<template #value>
										<span class="text-secondary max-w-40 truncate text-xs" :title="item.event">
											{{ item.event }}
										</span>
									</template>
								</Badge>
							</div>
						</n-scrollbar>
						<div class="flex justify-end">
							<n-button size="tiny" secondary @click="clearHistory">Clear history</n-button>
						</div>
					</div>
				</n-popover>
			</div>

			<n-input
				v-model:value="event"
				type="textarea"
				placeholder="Paste a single log line — auditd / syslog / Windows EventChannel / Suricata eve.json etc."
				:autosize="{ minRows: 3, maxRows: 8 }"
			/>

			<div class="flex flex-wrap items-center justify-between gap-3">
				<n-input-group size="small" class="flex-1">
					<n-input-group-label size="small" class="text-secondary!">Format</n-input-group-label>
					<n-select v-model:value="logFormat" :options="logFormatOptions" size="small" />
				</n-input-group>

				<div class="flex items-center gap-2">
					<n-button type="primary" size="small" :loading="testing" :disabled="!event.trim()" @click="runTest">
						<template #icon><Icon name="carbon:play" /></template>
						Test against Wazuh
					</n-button>
				</div>
			</div>
		</div>

		<div v-if="result" class="flex flex-col gap-2">
			<div class="flex justify-end">
				<n-button size="tiny" quaternary @click="clearResult">Clear test result</n-button>
			</div>

			<n-alert v-if="result.unavailable_reason" type="error" show-icon>
				<template #header>Logtest failed</template>
				{{ result.unavailable_reason }}
			</n-alert>

			<CardEntity v-else-if="!result.matched" size="small" status="warning">
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
			</CardEntity>

			<CardEntity v-else-if="result.rule" size="small" status="success">
				<template #headerMain>
					<div class="flex flex-wrap items-center justify-between gap-2">
						<div class="flex items-center gap-2">
							<Icon name="carbon:checkmark-filled" :size="16" class="text-success" />
							<span class="text-success text-sm font-semibold tracking-wide uppercase">Match</span>
						</div>
					</div>
				</template>
				<template #headerExtra>
					<n-button
						v-if="result.rule.id !== null"
						size="tiny"
						secondary
						@click="emit('open-rule', result.rule.id)"
					>
						<template #icon><Icon name="carbon:view" /></template>
						View in catalog
					</n-button>
				</template>

				<template #default>
					<div class="flex flex-col gap-2">
						<div class="text-sm">
							{{ result.rule.description }}
						</div>
						<div class="flex items-center gap-2">
							<Badge type="splitted" color="success" size="small">
								<template #label>Rule</template>
								<template #value>{{ result.rule.id }}</template>
							</Badge>
							<Badge type="splitted" :color="levelBadgeColor(result.rule.level)" size="small">
								<template #label>Level</template>
								<template #value>{{ result.rule.level ?? "—" }}</template>
							</Badge>
						</div>
					</div>
				</template>

				<template #mainExtra>
					<div class="flex flex-wrap gap-x-8 gap-y-5">
						<div v-if="result.rule.groups.length" class="flex flex-col gap-1">
							<span class="text-secondary text-3xs tracking-wider uppercase">Groups</span>
							<div class="flex flex-wrap gap-1.5">
								<n-tag v-for="item of result.rule.groups" :key="item" size="small">
									{{ item }}
								</n-tag>
							</div>
						</div>
						<div v-if="result.rule.mitre.length" class="flex flex-col gap-1">
							<span class="text-secondary text-3xs tracking-wider uppercase">MITRE ATT&CK</span>
							<div class="flex flex-wrap gap-1.5">
								<n-tag v-for="item of result.rule.mitre" :key="item" size="small">
									{{ item }}
								</n-tag>
							</div>
						</div>
						<div v-if="result.tactics.length" class="flex flex-col gap-1">
							<span class="text-secondary text-3xs tracking-wider uppercase">Tactics</span>
							<div class="flex flex-wrap gap-1.5">
								<n-tag v-for="item of result.tactics" :key="item" size="small">
									{{ item.toUpperCase() }}
								</n-tag>
							</div>
						</div>
					</div>
				</template>
			</CardEntity>

			<n-collapse v-if="result.alert" arrow-placement="right">
				<n-collapse-item name="alert" class="[&_.n-collapse-item\_\_content-inner]:pt-2!">
					<template #header>
						<span class="text-secondary text-sm">Decoded alert envelope</span>
					</template>
					<CodeSource :code="result.alert" />
				</n-collapse-item>
			</n-collapse>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CatalogLogTestResponse } from "@/types/detection-catalog"
import { useStorage } from "@vueuse/core"
import {
	NAlert,
	NButton,
	NCollapse,
	NCollapseItem,
	NInput,
	NInputGroup,
	NInputGroupLabel,
	NPopover,
	NScrollbar,
	NSelect,
	NTag,
	useMessage
} from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

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
const historyStorage = useStorage<unknown>(HISTORY_STORAGE_KEY, [], localStorage)
const history = ref<LogTestHistoryItem[]>([])

function clearResult() {
	result.value = null
}

function syncHistoryFromStorage() {
	try {
		const parsed = historyStorage.value
		history.value = Array.isArray(parsed)
			? parsed
					.filter(item => typeof item?.event === "string" && typeof item?.log_format === "string")
					.slice(0, HISTORY_MAX)
			: []
	} catch {
		/* Storage unavailable/corrupted: history is best-effort. */
		history.value = []
	}
}

function persistHistory() {
	try {
		historyStorage.value = history.value
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
			message.error(getApiErrorMessage(err as ApiError) || "Logtest request failed")
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

watch(
	() => historyStorage.value,
	() => {
		syncHistoryFromStorage()
	},
	{ immediate: true }
)
</script>
