<template>
	<div class="wazuh-rule-detail flex flex-col gap-4">
		<n-spin :show="loading">
			<template v-if="rule">
				<!-- Header strip: id / level / status / file -->
				<div class="flex flex-wrap gap-2">
					<Badge type="splitted">
						<template #label>ID</template>
						<template #value><code>{{ rule.id }}</code></template>
					</Badge>
					<Badge type="splitted" :color="levelColor">
						<template #label>Level</template>
						<template #value>{{ rule.level ?? "—" }}</template>
					</Badge>
					<Badge v-if="rule.status" type="splitted">
						<template #label>Status</template>
						<template #value>{{ rule.status }}</template>
					</Badge>
					<Badge v-if="rule.filename" type="splitted">
						<template #label>File</template>
						<template #value><code>{{ rule.filename }}</code></template>
					</Badge>
					<!-- Firing counts. Only shown when the indexer aggregation
					     succeeded — if it didn't, omitting these is better than
					     showing "0" for every rule (would imply "never fired",
					     not "we couldn't measure"). -->
					<Badge v-if="rule.firing_stats_available" type="splitted" :color="hitsColor">
						<template #label>Hits 30d</template>
						<template #value>{{ rule.hits_30d.toLocaleString() }}</template>
					</Badge>
					<Badge v-if="rule.firing_stats_available" type="splitted">
						<template #label>Hits 7d</template>
						<template #value>{{ rule.hits_7d.toLocaleString() }}</template>
					</Badge>
				</div>

				<!-- Description -->
				<section v-if="rule.description">
					<h4>Description</h4>
					<p class="text-secondary">{{ rule.description }}</p>
				</section>

				<!-- Groups -->
				<section v-if="rule.groups.length">
					<h4>Groups</h4>
					<div class="flex flex-wrap gap-1">
						<n-tag v-for="g of rule.groups" :key="g" size="small" type="info" :bordered="false">
							{{ g }}
						</n-tag>
					</div>
				</section>

				<!-- MITRE ATT&CK techniques (+ resolved tactic display names from
				     mitre_matrix) -->
				<section v-if="rule.mitre.length || rule.tactics.length">
					<h4>MITRE ATT&amp;CK</h4>
					<div class="flex flex-col gap-2">
						<div v-if="rule.mitre.length" class="flex flex-wrap gap-1">
							<n-tag v-for="t of rule.mitre" :key="t" size="small" :bordered="false">
								{{ t }}
							</n-tag>
						</div>
						<div v-if="rule.tactics.length" class="flex flex-wrap gap-1">
							<n-tag
								v-for="t of rule.tactics"
								:key="t"
								size="small"
								type="warning"
								:bordered="false"
							>
								{{ t }}
							</n-tag>
						</div>
					</div>
				</section>

				<!-- Compliance frameworks. We iterate the keys so the UI doesn't
				     hard-code the framework list — if Wazuh ever adds a new one,
				     it shows up automatically (frameworks with no values are
				     skipped). -->
				<section v-if="hasCompliance">
					<h4>Compliance</h4>
					<div class="flex flex-col gap-2">
						<div
							v-for="[label, values] of complianceEntries"
							:key="label"
							class="flex flex-wrap items-baseline gap-2"
						>
							<span class="compliance-label">{{ label }}</span>
							<n-tag
								v-for="v of values"
								:key="v"
								size="tiny"
								:bordered="false"
								class="font-mono"
							>
								{{ v }}
							</n-tag>
						</div>
					</div>
				</section>

				<!-- Rule Source — the synthesized <rule> XML block. Read-only
				     code view + Copy button so analysts can paste straight into
				     a local rule file when authoring exclusions / customizations.
				     Synthesized server-side from cached fields, not fetched from
				     the original .xml (see backend detection_catalog._synthesize_rule_xml). -->
				<section v-if="rule.source_xml">
					<div class="flex items-center justify-between gap-2">
						<h4>Rule Source</h4>
						<n-button size="tiny" quaternary @click="copySource">
							<template #icon><Icon name="carbon:copy" /></template>
							{{ copied ? "Copied" : "Copy" }}
						</n-button>
					</div>
					<pre class="rule-source"><code>{{ rule.source_xml }}</code></pre>
				</section>

				<!-- File location footer -->
				<section v-if="rule.relative_dirname">
					<h4>File location</h4>
					<p class="text-secondary text-xs font-mono">
						{{ rule.relative_dirname }}/{{ rule.filename }}
					</p>
				</section>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CatalogWazuhRuleDetailResponse } from "@/types/detectionCatalog.d"
import { NButton, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ ruleId: number }>()
const message = useMessage()

const rule = ref<CatalogWazuhRuleDetailResponse | null>(null)
const loading = ref(false)

// Transient "Copied" affordance on the Copy button. Resets on its own so
// the analyst doesn't see "Copied" forever after one click.
const copied = ref(false)
let copyResetHandle: ReturnType<typeof setTimeout> | null = null

async function copySource() {
	const xml = rule.value?.source_xml
	if (!xml) return
	try {
		await navigator.clipboard.writeText(xml)
	} catch {
		// Clipboard API can fail in HTTP-only contexts (no secure origin) or
		// when the browser refuses the permission. Fall back to a hidden
		// textarea + execCommand so the button still does something useful.
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

// Severity colour for the Level badge — same buckets as the index Level tag
// so the visual lines up when going row → modal.
const levelColor = computed(() => {
	const l = rule.value?.level
	if (l === null || l === undefined) return undefined
	if (l >= 12) return "danger"
	if (l >= 7) return "warning"
	if (l >= 3) return "info"
	return undefined
})

// Hit-count colour — rough buckets to signal "this rule is firing a lot
// right now". Same palette family as the level badge so the eye doesn't
// have to learn two scales.
const hitsColor = computed(() => {
	const h = rule.value?.hits_30d
	if (h === undefined || h === 0) return undefined
	if (h >= 10000) return "danger"
	if (h >= 1000) return "warning"
	if (h >= 100) return "info"
	return "success"
})

// Compliance entries with only the frameworks that actually have values.
// Empty arrays would just be visual noise.
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

function load(id: number) {
	loading.value = true
	rule.value = null
	Api.detectionCatalog
		.getWazuhRule(id)
		.then(res => {
			if (res.data?.success) {
				rule.value = res.data
			} else {
				message.warning(res.data?.message || "Failed to load Wazuh rule detail")
			}
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

// Re-fetch when the parent swaps `ruleId` (e.g. analyst opens a different
// rule without closing the modal).
watch(() => props.ruleId, id => load(id))
onBeforeMount(() => load(props.ruleId))
</script>

<style scoped lang="scss">
section h4 {
	margin: 0 0 6px 0;
	font-size: 0.92rem;
	font-weight: 600;
}

.compliance-label {
	display: inline-block;
	min-width: 90px;
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--fg-secondary-color);
}

/* Rule Source code block. Monospace, scrollable horizontally so long lines
   don't break the modal layout. Kept visually distinct from the rule-logic
   rows so analysts can see at a glance "this is the rule as-written". */
.rule-source {
	margin: 0;
	padding: 10px 12px;
	max-height: 320px;
	overflow: auto;
	font-family: var(--font-family-mono);
	font-size: 0.78rem;
	line-height: 1.45;
	color: var(--fg-default-color);
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px;
	white-space: pre;
	word-break: normal;
}
.rule-source code {
	display: block;
}
</style>
