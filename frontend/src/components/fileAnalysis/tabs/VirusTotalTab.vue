<template>
	<div class="@container flex flex-col gap-4">
		<n-empty
			v-if="!intel && !loading"
			description="No VirusTotal intelligence. The file is unknown to VirusTotal, or reputation is disabled."
			class="min-h-52 justify-center"
		/>

		<template v-else-if="intel">
			<!-- Headline as three hairline-separated cells rather than a free-flowing
			     row: same grid language as the summary card, so detection, classification
			     and community read as three answers instead of one paragraph. -->
			<div
				class="border-default bg-border grid gap-px overflow-hidden rounded-lg border @4xl:grid-cols-[auto_1fr_auto]"
			>
				<div class="bg-secondary flex items-center gap-4 p-4">
					<n-progress type="circle" :percentage="detPct" :color="ratioColor" :style="{ width: '76px' }">
						<div class="flex flex-col items-center">
							<span class="text-lg leading-none font-semibold">{{ reputation?.malicious ?? 0 }}</span>
							<span class="text-tertiary font-mono text-xs">/{{ reputation?.total ?? "?" }}</span>
						</div>
					</n-progress>
					<div class="flex flex-col gap-1">
						<span :class="SECTION_LABEL">Detection</span>
						<span class="text-secondary text-xs">engines flagging it</span>
					</div>
				</div>

				<div class="bg-secondary flex min-w-0 flex-col gap-2 p-4">
					<span :class="SECTION_LABEL">Threat label</span>
					<div v-if="intel.threat_label" class="flex min-w-0 items-center gap-2">
						<Icon :name="BugIcon" :size="15" class="text-error shrink-0" />
						<span class="text-default min-w-0 font-mono text-sm break-all">{{ intel.threat_label }}</span>
					</div>
					<span v-else class="text-tertiary text-sm">No consensus threat label.</span>

					<div v-if="intel.threat_categories?.length" class="flex flex-wrap gap-1">
						<n-tag
							v-for="c of intel.threat_categories"
							:key="c"
							type="error"
							size="small"
							round
							:bordered="false"
						>
							{{ c }}
						</n-tag>
						<n-tag v-for="n of intel.threat_names || []" :key="n" size="small" round :bordered="false">
							{{ n }}
						</n-tag>
					</div>
				</div>

				<!-- Community as aligned label/value rows: it used to run on as prose
				     ("Votes: 0 harmless · 0 malicious"), which hid the numbers. -->
				<div class="bg-secondary flex flex-col gap-2 p-4 @4xl:w-56">
					<span :class="SECTION_LABEL">Community</span>
					<div class="flex flex-col gap-1 text-xs">
						<div v-if="intel.reputation != null" class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">reputation</span>
							<span
								class="font-mono tabular-nums"
								:class="intel.reputation < 0 ? 'text-error' : 'text-secondary'"
							>
								{{ intel.reputation }}
							</span>
						</div>
						<div class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">harmless votes</span>
							<span class="text-success font-mono tabular-nums">{{ intel.harmless_votes ?? 0 }}</span>
						</div>
						<div class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">malicious votes</span>
							<span class="text-error font-mono tabular-nums">{{ intel.malicious_votes ?? 0 }}</span>
						</div>
						<div v-if="intel.times_submitted != null" class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">submitted</span>
							<span class="text-secondary font-mono tabular-nums">{{ intel.times_submitted }}×</span>
						</div>
					</div>
				</div>
			</div>

			<!-- File facts -->
			<div
				class="border-default bg-border grid gap-px overflow-hidden rounded-lg border @2xl:grid-cols-2 @4xl:grid-cols-4"
			>
				<div v-for="f in facts" :key="f.label" class="bg-secondary flex min-h-20 flex-col gap-1 p-4">
					<span :class="SECTION_LABEL">{{ f.label }}</span>
					<span class="text-default text-sm wrap-break-word">{{ f.value }}</span>
				</div>
			</div>

			<!-- VT sandbox behaviour — the detonation stand-in when our own sandbox is offline -->
			<CollapsibleCard v-if="intel.behaviour">
				<template #header>
					<span :class="SECTION_LABEL">Behaviour observed by VirusTotal's sandboxes</span>
					<n-tag size="tiny" round :bordered="false" type="info">no local detonation needed</n-tag>
				</template>

				<div class="@container flex flex-col gap-4 p-4 pb-0">
					<!-- Rows, not pills: a technique id is an identifier and its description
					     is prose, and packing both into a round tag produced ragged blobs
					     that could not be scanned down the ids. -->
					<!-- Rows, not pills: a technique id is an identifier and its description
					     is prose, and packing both into a round tag produced ragged blobs
					     that could not be scanned down the ids. -->
					<FilterableList
						v-if="intel.behaviour.mitre?.length"
						:items="intel.behaviour.mitre"
						label="MITRE ATT&CK"
						:filter-keys="['id', 'description']"
						filter-placeholder="Filter by technique or text"
						max-height="16rem"
						empty-text="No technique matches that filter."
						:card="false"
						row-class="flex flex-wrap items-baseline gap-x-3 gap-y-1"
					>
						<template #item="{ item: t }">
							<span class="text-warning w-24 shrink-0 font-mono text-xs">{{ t.id }}</span>
							<span v-if="t.description" class="text-secondary min-w-0 text-xs">{{ t.description }}</span>
						</template>
					</FilterableList>

					<div
						class="bg-secondary divide-border border-border -mx-4 grid gap-3 divide-y border-y @4xl:grid-cols-3 @4xl:divide-x @4xl:divide-y-0"
					>
						<div class="p-4">
							<ValueList label="Contacted IPs" :items="intel.behaviour.contacted_ips" :link="ipUrl" />
						</div>
						<div class="p-4">
							<ValueList
								label="Contacted domains"
								:items="intel.behaviour.contacted_domains"
								:link="domainUrl"
							/>
						</div>

						<div class="p-4">
							<ValueList label="Contacted URLs" :items="intel.behaviour.contacted_urls" />
						</div>
					</div>

					<!-- Two zones on one baseline: what the file IS on the left, what
					     identifies it right-aligned. The old row mixed a bold name, a round
					     tag and a break-all hash in one flow, so long names shoved the hash
					     onto a second ragged line. -->
					<FilterableList
						v-if="intel.behaviour.dropped_files?.length"
						:items="intel.behaviour.dropped_files"
						label="Dropped files"
						:filter-keys="['name', 'type', 'sha256']"
						filter-placeholder="Filter by name, type or hash"
						max-height="13rem"
						empty-text="No dropped file matches that filter."
						:card="false"
						row-class="flex flex-wrap items-baseline gap-x-3 gap-y-1"
					>
						<template #item="{ item: d }">
							<div class="flex min-w-0 grow items-baseline gap-2">
								<Icon
									:name="iconForFile(d.name)"
									:size="13"
									class="text-secondary shrink-0 translate-y-0.5"
								/>
								<span class="text-default min-w-0 truncate font-mono text-xs" :title="d.name">
									{{ d.name || "(unnamed)" }}
								</span>
							</div>
							<span v-if="droppedMeta(d)" class="text-tertiary text-2xs shrink-0 font-mono">
								{{ droppedMeta(d) }}
							</span>
						</template>
					</FilterableList>

					<div
						class="bg-secondary divide-border border-border -mx-4 grid gap-3 divide-y border-t @4xl:grid-cols-3 @4xl:divide-x @4xl:divide-y-0"
					>
						<div class="p-4">
							<ValueList label="Processes" :items="intel.behaviour.processes" />
						</div>
						<div class="p-4">
							<ValueList label="Registry keys" :items="intel.behaviour.registry_keys" />
						</div>
						<div class="p-4">
							<ValueList label="Mutexes" :items="intel.behaviour.mutexes" />
						</div>
					</div>
				</div>
			</CollapsibleCard>

			<!-- Crowdsourced detection rules -->
			<!-- Same card shape as the Behaviour block: a header band carrying the label,
			     the count and the filter, then the rows. Loose labels floating above bare
			     boxes were what made this tab read as a pile of fragments. -->
			<!-- Crowdsourced detection rules -->
			<FilterableList
				v-if="intel.yara?.length"
				:items="intel.yara"
				label="Crowdsourced YARA"
				:filter-keys="['rule', 'author', 'ruleset', 'description']"
				filter-placeholder="Filter by rule, author or ruleset"
				empty-text="No rule matches that filter."
				row-class="flex flex-col gap-1"
			>
				<template #item="{ item: y }">
					<!-- Two zones on one baseline: the rule identity on the left, its
					     provenance right-aligned. -->
					<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
						<div class="flex min-w-0 grow items-baseline gap-2">
							<Icon :name="RuleIcon" :size="13" class="text-warning shrink-0 translate-y-0.5" />
							<!-- mono: a YARA rule name is an identifier, not prose -->
							<span class="text-default min-w-0 truncate font-mono text-xs font-medium" :title="y.rule">
								{{ y.rule }}
							</span>
						</div>
						<span v-if="yaraMeta(y)" class="text-tertiary text-2xs shrink-0 font-mono">
							{{ yaraMeta(y) }}
						</span>
					</div>
					<!-- Indented past the icon so it reads as belonging to the rule above. -->
					<span v-if="y.description" class="text-secondary pl-5 text-xs">{{ y.description }}</span>
				</template>
			</FilterableList>

			<FilterableList
				v-if="intel.sigma?.length"
				:items="intel.sigma"
				label="Sigma matches"
				row-class="flex flex-wrap items-center gap-2 text-xs"
			>
				<template #item="{ item: sig }">
					<n-tag size="tiny" round :bordered="false" :type="sevTag(sig.level)">
						{{ sig.level || "—" }}
					</n-tag>
					<span class="text-default min-w-0">{{ sig.title }}</span>
					<span v-if="sig.source" class="text-tertiary">· {{ sig.source }}</span>
				</template>
			</FilterableList>

			<FilterableList
				v-if="intel.ids?.length"
				:items="intel.ids"
				label="IDS/IPS alerts"
				row-class="flex flex-wrap items-center gap-2 text-xs"
			>
				<template #item="{ item: x }">
					<n-tag size="tiny" round :bordered="false" :type="sevTag(x.severity)">
						{{ x.severity || "—" }}
					</n-tag>
					<span class="text-default min-w-0 break-all">{{ x.msg }}</span>
					<span v-if="x.source" class="text-tertiary">· {{ x.source }}</span>
				</template>
			</FilterableList>

			<!-- Per-engine detections (collapsed by default; can be long) -->
			<n-collapse v-if="intel.detections?.length">
				<n-collapse-item
					:title="`Engine detections (${intel.detection_count ?? intel.detections.length})`"
					name="det"
				>
					<div class="border-default rounded-lg border">
						<n-scrollbar style="max-height: 20rem">
							<div class="divide-border flex flex-col divide-y">
								<div
									v-for="(d, i) of intel.detections"
									:key="i"
									class="flex items-center gap-2 px-3 py-1.5 text-xs"
								>
									<Icon
										:name="DotIcon"
										:size="10"
										class="shrink-0"
										:class="d.category === 'malicious' ? 'text-error' : 'text-warning'"
									/>
									<!-- Engine name in a fixed mono column so the verdicts line up
									     and the list can be scanned down one edge. -->
									<span class="text-secondary w-44 shrink-0 font-mono">{{ d.engine }}</span>
									<span class="text-default min-w-0 font-mono break-all">{{ d.result }}</span>
								</div>
							</div>
						</n-scrollbar>
					</div>
				</n-collapse-item>
			</n-collapse>

			<div class="flex items-center gap-3 text-xs">
				<a
					v-if="permalink"
					:href="permalink"
					target="_blank"
					rel="noopener noreferrer"
					class="hover:text-primary underline"
				>
					Full report on VirusTotal ↗
				</a>
				<span class="text-secondary">
					VirusTotal aggregates 70+ engines and multiple community sandboxes — treat it as corroboration, not
					ground truth.
				</span>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisReputation } from "@/types/file-analysis"
import { NCollapse, NCollapseItem, NEmpty, NProgress, NScrollbar, NTag } from "naive-ui"
import { computed } from "vue"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import FilterableList from "@/components/common/FilterableList.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import ValueList from "@/components/common/ValueList.vue"
import { iconForFile, virusTotalUrl } from "@/components/fileAnalysis/fileAnalysis.helpers"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"

const props = defineProps<{ reputation?: FileAnalysisReputation | null; loading?: boolean }>()

const BugIcon = "carbon:debug"
const RuleIcon = "carbon:rule"
const DotIcon = "carbon:circle-solid"

const dFormats = useSettingsStore().dateFormat

const intel = computed(() => props.reputation?.intel ?? null)
const permalink = computed(() => props.reputation?.permalink)

const detPct = computed(() => {
	const m = props.reputation?.malicious ?? 0
	const t = props.reputation?.total ?? 0
	return t > 0 ? Math.min(100, Math.round((m / t) * 100)) : 0
})
// The ratio is graded by hit count, not by our own verdict — five engines calling
// a file bad is a different statement from one. Theme variables, so the ring
// follows the light/dark switch instead of staying at a fixed hex.
const ratioColor = computed(() => {
	const m = props.reputation?.malicious ?? 0
	if (m >= 5) return "var(--error-color)"
	if (m >= 1) return "var(--warning-color)"
	return "var(--success-color)"
})

const facts = computed(() => {
	const i = intel.value
	if (!i) return []
	const rows: { label: string; value: string }[] = []
	if (i.type_description) rows.push({ label: "Type", value: i.type_description })
	if (i.size != null) rows.push({ label: "Size", value: formatBytes(i.size) ?? "—" })
	if (i.first_seen) rows.push({ label: "First seen", value: String(formatDate(i.first_seen, dFormats.date)) })
	if (i.last_analysis)
		rows.push({ label: "Last analysis", value: String(formatDate(i.last_analysis, dFormats.date)) })
	rows.push({ label: "Signed", value: i.signed ? i.signer || "yes" : "no" })
	if (i.names?.length) rows.push({ label: "Also seen as", value: i.names.slice(0, 3).join(", ") })
	return rows
})

/** Type and hash as one muted run — both identify the file, so both read alike. */
function droppedMeta(d: { type?: string; sha256?: string }): string {
	return [d.type, d.sha256 ? d.sha256.slice(0, 12) : ""].filter(Boolean).join(" · ")
}

/** Ruleset and author as one muted run — both are provenance, so both read alike. */
function yaraMeta(y: { ruleset?: string; author?: string }): string {
	return [y.ruleset, y.author].filter(Boolean).join(" · ")
}

function sevTag(level?: string): "error" | "warning" | "default" {
	const l = (level || "").toLowerCase()
	if (l.includes("critical") || l.includes("high")) return "error"
	if (l.includes("medium")) return "warning"
	return "default"
}
function ipUrl(v: string): string {
	return virusTotalUrl(v, "ip")
}
function domainUrl(v: string): string {
	return virusTotalUrl(v, "domain")
}
</script>
