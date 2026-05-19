<template>
	<div class="wazuh-rule-detail flex flex-col gap-4">
		<n-spin :show="loading">
			<template v-if="rule">
				<!-- HERO HEADER -----------------------------------------
				     Big rule ID + description + key metadata badges in a
				     compact card. The "card-status-*" variants tint the
				     whole header by severity so the analyst's first glance
				     conveys risk level. -->
				<CardEntity size="medium" :status="hitsCardStatus">
					<template #headerMain>
						<div class="flex items-start gap-3">
							<span :class="levelTagClass(rule.level)" class="rule-level-hero">
								{{ rule.level ?? "—" }}
							</span>
							<div class="flex flex-col gap-1">
								<div class="text-tertiary text-xs uppercase tracking-wide">
									Wazuh Rule
								</div>
								<div class="text-xl font-semibold leading-tight">
									Rule {{ rule.id }}
								</div>
								<div v-if="rule.description" class="text-secondary text-sm leading-snug">
									{{ rule.description }}
								</div>
							</div>
						</div>
					</template>

					<template #default>
						<div class="flex flex-wrap gap-2">
							<Badge v-if="rule.status" type="splitted" color="success">
								<template #label>Status</template>
								<template #value>{{ rule.status }}</template>
							</Badge>
							<Badge v-if="rule.firing_stats_available" type="splitted" :color="hitsBadgeColor">
								<template #label>Hits 30d</template>
								<template #value>{{ rule.hits_30d.toLocaleString() }}</template>
							</Badge>
							<Badge v-if="rule.firing_stats_available" type="splitted">
								<template #label>Hits 7d</template>
								<template #value>{{ rule.hits_7d.toLocaleString() }}</template>
							</Badge>
							<Badge
								v-if="rule.firing_stats_available && rule.last_seen"
								type="splitted"
								color="primary"
							>
								<template #label>Last fired</template>
								<template #value>{{ formatRelativeTime(rule.last_seen) }}</template>
							</Badge>
							<Badge v-if="rule.filename" type="splitted">
								<template #label>File</template>
								<template #value><code>{{ rule.filename }}</code></template>
							</Badge>
						</div>
					</template>
				</CardEntity>

				<!-- Groups -->
				<CardEntity v-if="rule.groups.length" size="small">
					<template #headerMain>
						<SectionLabel icon="carbon:tag" label="Groups" />
					</template>
					<template #default>
						<div class="flex flex-wrap gap-1.5">
							<span v-for="g of rule.groups" :key="g" class="group-pill">
								{{ g }}
							</span>
						</div>
					</template>
				</CardEntity>

				<!-- MITRE ATT&CK -->
				<CardEntity v-if="rule.mitre.length || rule.tactics.length" size="small">
					<template #headerMain>
						<SectionLabel icon="carbon:flag" label="MITRE ATT&CK" />
					</template>
					<template #default>
						<div class="flex flex-col gap-2">
							<div v-if="rule.mitre.length" class="flex flex-wrap gap-1.5">
								<span v-for="t of rule.mitre" :key="t" class="mitre-pill">{{ t }}</span>
							</div>
							<div v-if="rule.tactics.length" class="flex flex-wrap gap-1.5">
								<span v-for="t of rule.tactics" :key="t" class="tactic-pill">
									{{ t.toUpperCase() }}
								</span>
							</div>
						</div>
					</template>
				</CardEntity>

				<!-- Compliance — only render frameworks that actually have values. -->
				<CardEntity v-if="hasCompliance" size="small">
					<template #headerMain>
						<SectionLabel icon="carbon:certificate-check" label="Compliance" />
					</template>
					<template #default>
						<div class="compliance-grid">
							<div
								v-for="[label, values] of complianceEntries"
								:key="label"
								class="compliance-row"
							>
								<div class="compliance-label">{{ label }}</div>
								<div class="flex flex-wrap gap-1">
									<span
										v-for="v of values"
										:key="v"
										class="compliance-control"
									>
										{{ v }}
									</span>
								</div>
							</div>
						</div>
					</template>
				</CardEntity>

				<!-- Rule Source ---------------------------------------------
				     Reconstructed <rule> XML block. Copy button on the right
				     for paste-into-rule-file workflows. -->
				<CardEntity v-if="rule.source_xml" size="small">
					<template #header>
						<div class="flex items-center justify-between gap-2">
							<SectionLabel icon="carbon:code" label="Rule Source" />
							<n-button size="tiny" quaternary @click="copySource">
								<template #icon><Icon name="carbon:copy" /></template>
								{{ copied ? "Copied" : "Copy XML" }}
							</n-button>
						</div>
					</template>
					<template #default>
						<pre class="rule-source"><code>{{ rule.source_xml }}</code></pre>
					</template>
				</CardEntity>

				<!-- File location footer -->
				<CardEntity v-if="rule.relative_dirname" size="small" embedded>
					<template #default>
						<div class="flex items-center gap-2 text-xs">
							<Icon name="carbon:folder" :size="12" />
							<span class="text-tertiary">Location:</span>
							<code class="font-mono">{{ rule.relative_dirname }}/{{ rule.filename }}</code>
						</div>
					</template>
				</CardEntity>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CatalogWazuhRuleDetailResponse } from "@/types/detectionCatalog.d"
import { NButton, NSpin, useMessage } from "naive-ui"
import { computed, defineComponent, h, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

// Tiny inline component for section labels — keeps the four section headers
// visually identical without copy-pasting the markup.
const SectionLabel = defineComponent({
	props: { icon: String, label: String },
	setup(props) {
		return () =>
			h("div", { class: "flex items-center gap-2" }, [
				props.icon ? h(Icon, { name: props.icon, size: 14 }) : null,
				h(
					"span",
					{ class: "text-sm font-semibold uppercase tracking-wide" },
					props.label
				)
			])
	}
})

const props = defineProps<{ ruleId: number }>()
const message = useMessage()

const rule = ref<CatalogWazuhRuleDetailResponse | null>(null)
const loading = ref(false)

const copied = ref(false)
let copyResetHandle: ReturnType<typeof setTimeout> | null = null

// Severity classes for the big hero level badge — same buckets as the
// index column. Single source of truth at the top so they stay in sync.
function levelTagClass(level: number | null | undefined): string {
	if (level === null || level === undefined) return "level-pill level-none"
	if (level >= 12) return "level-pill level-critical"
	if (level >= 7) return "level-pill level-warning"
	if (level >= 3) return "level-pill level-info"
	return "level-pill level-low"
}

// Pick a card status tint for the hero based on hit volume — lets the modal
// signal "this rule is hot right now" without screaming.
const hitsCardStatus = computed<"success" | "warning" | "error" | undefined>(() => {
	if (!rule.value?.firing_stats_available) return undefined
	const h = rule.value.hits_30d
	if (h >= 10000) return "error"
	if (h >= 1000) return "warning"
	return undefined
})

const hitsBadgeColor = computed<"danger" | "warning" | "primary" | "success" | undefined>(() => {
	const h = rule.value?.hits_30d
	if (h === undefined || h === 0) return undefined
	if (h >= 10000) return "danger"
	if (h >= 1000) return "warning"
	if (h >= 100) return "primary"
	return "success"
})

const complianceEntries = computed<[string, string[]][]>(() => {
	const c = rule.value?.compliance
	if (!c) return []
	const labels: Record<string, string> = {
		pci_dss: "PCI DSS",
		gdpr: "GDPR",
		hipaa: "HIPAA",
		nist_800_53: "NIST 800-53",
		tsc: "TSC",
		gpg13: "GPG13"
	}
	return Object.entries(c)
		.filter(([, v]) => Array.isArray(v) && v.length > 0)
		.map(([k, v]) => [labels[k] ?? k, v as string[]])
})

const hasCompliance = computed(() => complianceEntries.value.length > 0)

function formatRelativeTime(iso: string): string {
	const then = new Date(iso).getTime()
	if (Number.isNaN(then)) return iso
	const diffMs = Date.now() - then
	if (diffMs < 0) return "just now"
	const sec = Math.floor(diffMs / 1000)
	if (sec < 60) return `${sec}s ago`
	const min = Math.floor(sec / 60)
	if (min < 60) return `${min}m ago`
	const hr = Math.floor(min / 60)
	if (hr < 24) return `${hr}h ago`
	const day = Math.floor(hr / 24)
	if (day < 30) return `${day}d ago`
	return `${Math.floor(day / 30)}mo ago`
}

async function copySource() {
	const xml = rule.value?.source_xml
	if (!xml) return
	try {
		await navigator.clipboard.writeText(xml)
	} catch {
		// Clipboard API fails in HTTP-only contexts / no permission. Fallback
		// via the hidden-textarea trick.
		const ta = document.createElement("textarea")
		ta.value = xml
		ta.setAttribute("readonly", "")
		ta.style.position = "absolute"
		ta.style.left = "-9999px"
		document.body.appendChild(ta)
		ta.select()
		try {
			document.execCommand("copy")
		} finally {
			document.body.removeChild(ta)
		}
	}
	copied.value = true
	if (copyResetHandle) clearTimeout(copyResetHandle)
	copyResetHandle = setTimeout(() => {
		copied.value = false
	}, 1500)
}

function load(id: number) {
	loading.value = true
	rule.value = null
	Api.detectionCatalog
		.getWazuhRule(id)
		.then(res => {
			if (res.data?.success) rule.value = res.data
			else message.warning(res.data?.message || "Failed to load Wazuh rule detail")
		})
		.catch(err => {
			const status = err.response?.status
			if (status === 404) {
				message.warning(`Wazuh rule ${id} not found in the cache`)
			} else {
				message.error(err.response?.data?.detail || err.response?.data?.message || "Failed to load Wazuh rule detail")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

watch(() => props.ruleId, id => load(id))
onBeforeMount(() => load(props.ruleId))
</script>

<style scoped lang="scss">
.rule-level-hero {
	min-width: 44px !important;
	height: 44px !important;
	font-size: 1.25rem !important;
	border-radius: 10px !important;
	flex-shrink: 0;
}

/* Level pills — shared with the index table for consistency. */
.level-pill {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 28px;
	height: 22px;
	padding: 0 6px;
	font-size: 0.78rem;
	font-weight: 600;
	font-family: var(--font-family-mono);
	border-radius: 5px;
	border: 1px solid transparent;
}
.level-pill.level-none {
	color: var(--fg-secondary-color);
	opacity: 0.6;
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}
.level-pill.level-low {
	color: var(--fg-secondary-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}
.level-pill.level-info {
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.1);
	border-color: rgba(var(--primary-color-rgb) / 0.25);
}
.level-pill.level-warning {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.12);
	border-color: rgba(var(--warning-color-rgb) / 0.3);
}
.level-pill.level-critical {
	color: var(--error-color);
	background-color: rgba(var(--error-color-rgb) / 0.1);
	border-color: rgba(var(--error-color-rgb) / 0.3);
}

.group-pill {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	font-size: 0.72rem;
	font-weight: 500;
	border-radius: 999px;
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.08);
	border: 1px solid rgba(var(--primary-color-rgb) / 0.18);
}

.mitre-pill {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	font-size: 0.72rem;
	font-family: var(--font-family-mono);
	font-weight: 500;
	border-radius: 6px;
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
}

.tactic-pill {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	font-size: 0.7rem;
	font-weight: 600;
	letter-spacing: 0.04em;
	border-radius: 999px;
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.1);
	border: 1px solid rgba(var(--warning-color-rgb) / 0.25);
}

/* Compliance grid — framework labels on the left, control values on the right.
   Grid columns let the labels align vertically when there are multiple. */
.compliance-grid {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.compliance-row {
	display: grid;
	grid-template-columns: 110px 1fr;
	align-items: start;
	gap: 12px;
}
.compliance-label {
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--fg-secondary-color);
	padding-top: 3px;
}
.compliance-control {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	font-size: 0.72rem;
	font-family: var(--font-family-mono);
	border-radius: 5px;
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
}

.rule-source {
	margin: 0;
	padding: 12px 14px;
	max-height: 360px;
	overflow: auto;
	font-family: var(--font-family-mono);
	font-size: 0.78rem;
	line-height: 1.5;
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px;
	white-space: pre;
}
.rule-source code {
	display: block;
}
</style>
