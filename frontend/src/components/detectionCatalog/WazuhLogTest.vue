<template>
	<!--
		Logtest panel. Sits above the Wazuh Rules table as a collapsible
		card. Cleaner than its own tab — analysts who want to test a log
		against the catalog stay in the same surface. Collapsed by default
		so it's discoverable but doesn't push the table down on every load.
	-->
	<n-collapse :default-expanded-names="[]" arrow-placement="right">
		<n-collapse-item title="Test a log line" name="logtest">
			<template #header-extra>
				<span class="text-tertiary text-xs">
					Paste a log, see which Wazuh rule fires
				</span>
			</template>

			<div class="flex flex-col gap-3">
				<n-input
					v-model:value="event"
					type="textarea"
					placeholder="Paste a single log line here — e.g. an auditd/syslog/Windows-EventChannel entry as the agent would forward it…"
					:autosize="{ minRows: 3, maxRows: 8 }"
					class="font-mono"
				/>

				<div class="flex flex-wrap items-center gap-3">
					<div class="flex items-center gap-2">
						<span class="text-tertiary text-xs">Format</span>
						<n-select
							v-model:value="logFormat"
							:options="logFormatOptions"
							size="small"
							style="width: 160px"
						/>
					</div>

					<n-button
						type="primary"
						size="small"
						:loading="testing"
						:disabled="!event.trim()"
						@click="runTest"
					>
						Test against Wazuh
					</n-button>

					<n-button v-if="result" size="small" quaternary @click="clearResult">
						Clear
					</n-button>
				</div>

				<!-- Result panel. Three shapes:
				     1. unavailable_reason set → render error alert
				     2. matched=false → "No rule matched" + decoded preview if any
				     3. matched=true → matched rule card with deep-link into the
				        catalog modal for full detail -->
				<template v-if="result">
					<n-alert v-if="result.unavailable_reason" type="error" :show-icon="true">
						<template #header>Logtest failed</template>
						{{ result.unavailable_reason }}
					</n-alert>

					<n-alert v-else-if="!result.matched" type="info" :show-icon="true">
						<template #header>No rule matched</template>
						Wazuh saw the log but no analyst-facing rule fired. This usually means the
						decoder didn't recognize the format — try a different "Format" above, or
						confirm the log shape matches what your agents actually forward.
					</n-alert>

					<div v-else-if="result.rule" class="match-card flex flex-col gap-3">
						<div class="flex flex-wrap items-center gap-2">
							<span class="font-semibold">Match:</span>
							<n-tag type="success" :bordered="false">
								Rule {{ result.rule.id }}
							</n-tag>
							<n-tag size="small" :bordered="false" :type="levelTagType(result.rule.level)">
								Level {{ result.rule.level ?? "—" }}
							</n-tag>
							<n-button
								v-if="result.rule.id !== null"
								size="tiny"
								quaternary
								@click="emit('open-rule', result.rule.id!)"
							>
								<template #icon><Icon name="carbon:arrow-right" /></template>
								View in catalog
							</n-button>
						</div>

						<p class="text-secondary">{{ result.rule.description }}</p>

						<div v-if="result.rule.groups.length" class="flex flex-wrap gap-1">
							<n-tag
								v-for="g of result.rule.groups"
								:key="g"
								size="tiny"
								type="info"
								:bordered="false"
							>
								{{ g }}
							</n-tag>
						</div>

						<div
							v-if="result.rule.mitre.length || result.tactics.length"
							class="flex flex-wrap gap-1"
						>
							<n-tag v-for="t of result.rule.mitre" :key="t" size="tiny" :bordered="false">
								{{ t }}
							</n-tag>
							<n-tag
								v-for="t of result.tactics"
								:key="t"
								size="tiny"
								type="warning"
								:bordered="false"
							>
								{{ t }}
							</n-tag>
						</div>
					</div>

					<!-- Decoded alert envelope, collapsible — useful for debugging
					     when an analyst expected a different rule and wants to see
					     what Wazuh actually decoded. -->
					<n-collapse v-if="result.alert">
						<n-collapse-item title="Decoded alert envelope" name="alert">
							<pre class="alert-envelope"><code>{{ formatAlert(result.alert) }}</code></pre>
						</n-collapse-item>
					</n-collapse>
				</template>
			</div>
		</n-collapse-item>
	</n-collapse>
</template>

<script setup lang="ts">
import type { CatalogLogTestResponse } from "@/types/detectionCatalog.d"
import {
	NAlert,
	NButton,
	NCollapse,
	NCollapseItem,
	NInput,
	NSelect,
	NTag,
	useMessage
} from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

// Emits a "open-rule" event when the user clicks "View in catalog" on a
// matched rule — parent (WazuhRulesIndex) handles opening the modal so we
// don't duplicate the modal-mounting logic in two places.
const emit = defineEmits<{
	(e: "open-rule", ruleId: number): void
}>()

const message = useMessage()

const event = ref("")
// Wazuh's most common log formats — covers ~95% of what analysts paste.
// "syslog" is the safe default and works for most agent-forwarded logs.
const logFormat = ref("syslog")
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

function clearResult() {
	result.value = null
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

// Same level → tag colour mapping as WazuhRulesIndex — keep the visual
// consistent across surfaces.
function levelTagType(level: number | null): "default" | "info" | "warning" | "error" | "success" {
	if (level === null || level === undefined) return "default"
	if (level >= 12) return "error"
	if (level >= 7) return "warning"
	if (level >= 3) return "info"
	return "default"
}

function formatAlert(alert: Record<string, unknown>): string {
	// Pretty-print 2-space indented JSON; matches what most operators see
	// in their SIEM dashboards.
	try {
		return JSON.stringify(alert, null, 2)
	} catch {
		return String(alert)
	}
}
</script>

<style scoped lang="scss">
.match-card {
	padding: 12px 14px;
	background: rgba(var(--primary-color-rgb) / 0.06);
	border: 1px solid rgba(var(--primary-color-rgb) / 0.2);
	border-radius: 6px;
}

.alert-envelope {
	margin: 0;
	padding: 10px 12px;
	max-height: 300px;
	overflow: auto;
	font-family: var(--font-family-mono);
	font-size: 0.75rem;
	line-height: 1.45;
	color: var(--fg-default-color);
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px;
	white-space: pre;
	word-break: normal;
}
.alert-envelope code {
	display: block;
}
</style>
