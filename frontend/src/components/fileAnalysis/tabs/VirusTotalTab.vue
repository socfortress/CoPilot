<template>
	<div class="flex flex-col gap-4">
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
				class="border-default bg-border grid gap-px overflow-hidden rounded-lg border lg:grid-cols-[auto_1fr_auto]"
			>
				<div class="bg-secondary flex items-center gap-4 p-4">
					<n-progress type="circle" :percentage="detPct" :color="ratioColor" :style="{ width: '76px' }">
						<div class="flex flex-col items-center">
							<span class="text-lg leading-none font-semibold">{{ reputation?.malicious ?? 0 }}</span>
							<span class="text-tertiary font-mono text-xs">/{{ reputation?.total ?? "?" }}</span>
						</div>
					</n-progress>
					<div class="flex flex-col gap-1">
						<span :class="LABEL">Detection</span>
						<span class="text-secondary text-xs">engines flagging it</span>
					</div>
				</div>

				<div class="bg-secondary flex min-w-0 flex-col gap-2 p-4">
					<span :class="LABEL">Threat label</span>
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
				<div class="bg-secondary flex flex-col gap-2 p-4 lg:w-56">
					<span :class="LABEL">Community</span>
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
				class="border-default bg-border grid gap-px overflow-hidden rounded-lg border sm:grid-cols-2 lg:grid-cols-4"
			>
				<div v-for="f in facts" :key="f.label" class="bg-secondary flex min-h-20 flex-col gap-1 p-4">
					<span :class="LABEL">{{ f.label }}</span>
					<span class="text-default text-sm wrap-break-word">{{ f.value }}</span>
				</div>
			</div>

			<!-- VT sandbox behaviour — the detonation stand-in when our own sandbox is offline -->
			<div v-if="intel.behaviour" class="border-default flex flex-col overflow-hidden rounded-lg border">
				<div class="border-default bg-secondary flex flex-wrap items-center gap-2 border-b px-4 py-2">
					<span :class="LABEL">Behaviour observed by VirusTotal's sandboxes</span>
					<n-tag size="tiny" round :bordered="false" type="info">no local detonation needed</n-tag>
				</div>

				<div class="flex flex-col gap-4 p-4">
					<!-- Rows, not pills: a technique id is an identifier and its description
					     is prose, and packing both into a round tag produced ragged blobs
					     that could not be scanned down the ids. -->
					<div v-if="intel.behaviour.mitre?.length" class="flex flex-col gap-2">
						<div class="flex flex-wrap items-center justify-between gap-2">
							<span :class="LABEL">
								MITRE ATT&CK
								<span class="text-tertiary normal-case">
									({{ filteredMitre.length }}/{{ intel.behaviour.mitre.length }})
								</span>
							</span>
							<!-- Filtering happens in memory over the techniques already loaded
							     with the report: no request is made as you type. -->
							<n-input
								v-model:value="mitreQuery"
								size="tiny"
								clearable
								placeholder="Filter by technique or text"
								class="w-full sm:w-64"
							>
								<template #prefix><Icon :name="SearchIcon" :size="13" /></template>
							</n-input>
						</div>

						<div class="border-default rounded-lg border">
							<n-scrollbar style="max-height: 16rem">
								<div class="divide-border flex flex-col divide-y">
									<!-- Composite key: VirusTotal reports the same technique more than
									     once (different tactic or description), so the id alone is not
									     unique and Vue warns about duplicate keys. -->
									<div
										v-for="(t, ti) of filteredMitre"
										:key="`${t.id}-${ti}`"
										class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2"
									>
										<span class="text-warning w-24 shrink-0 font-mono text-xs">{{ t.id }}</span>
										<span v-if="t.description" class="text-secondary min-w-0 text-xs">
											{{ t.description }}
										</span>
									</div>
									<div v-if="!filteredMitre.length" class="text-tertiary px-3 py-4 text-xs">
										No technique matches that filter.
									</div>
								</div>
							</n-scrollbar>
						</div>
					</div>

					<div class="grid gap-3 md:grid-cols-3">
						<IocList label="Contacted IPs" :items="intel.behaviour.contacted_ips" :link="ipUrl" />
						<IocList
							label="Contacted domains"
							:items="intel.behaviour.contacted_domains"
							:link="domainUrl"
						/>
						<IocList label="Contacted URLs" :items="intel.behaviour.contacted_urls" />
					</div>

					<div v-if="intel.behaviour.dropped_files?.length" class="flex flex-col gap-2">
						<div class="flex flex-wrap items-center justify-between gap-2">
							<span :class="LABEL">
								Dropped files
								<span class="text-tertiary normal-case">
									({{ filteredDropped.length }}/{{ intel.behaviour.dropped_files.length }})
								</span>
							</span>
							<n-input
								v-model:value="droppedQuery"
								size="tiny"
								clearable
								placeholder="Filter by name, type or hash"
								class="w-full sm:w-64"
							>
								<template #prefix><Icon :name="SearchIcon" :size="13" /></template>
							</n-input>
						</div>
						<div class="border-default rounded-lg border">
							<n-scrollbar style="max-height: 13rem">
								<div class="divide-border flex flex-col divide-y">
									<!-- Same two-zone row as the YARA list: what the file IS on the
									     left, what identifies it right-aligned. The old row mixed a
									     bold name, a round tag and a break-all hash in one flow, so
									     long names shoved the hash onto a second ragged line. -->
									<div
										v-for="(d, i) of filteredDropped"
										:key="i"
										class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2"
									>
										<div class="flex min-w-0 grow items-baseline gap-2">
											<Icon
												:name="iconForFile(d.name)"
												:size="13"
												class="text-secondary shrink-0 translate-y-0.5"
											/>
											<span
												class="text-default min-w-0 truncate font-mono text-xs"
												:title="d.name"
											>
												{{ d.name || "(unnamed)" }}
											</span>
										</div>
										<span v-if="droppedMeta(d)" class="text-tertiary shrink-0 font-mono text-2xs">
											{{ droppedMeta(d) }}
										</span>
									</div>
									<div v-if="!filteredDropped.length" class="text-tertiary px-3 py-4 text-xs">
										No dropped file matches that filter.
									</div>
								</div>
							</n-scrollbar>
						</div>
					</div>

					<div class="grid gap-3 md:grid-cols-3">
						<IocList label="Processes" :items="intel.behaviour.processes" mono />
						<IocList label="Registry keys" :items="intel.behaviour.registry_keys" mono />
						<IocList label="Mutexes" :items="intel.behaviour.mutexes" mono />
					</div>
				</div>
			</div>

			<!-- Crowdsourced detection rules -->
			<!-- Same card shape as the Behaviour block: a header band carrying the label,
			     the count and the filter, then the rows. Loose labels floating above bare
			     boxes were what made this tab read as a pile of fragments. -->
			<div v-if="intel.yara?.length" class="border-default flex flex-col overflow-hidden rounded-lg border">
				<div
					class="border-default bg-secondary flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2"
				>
					<span :class="LABEL">
						Crowdsourced YARA
						<span class="text-tertiary normal-case">
							({{ filteredYara.length }}/{{ intel.yara.length }})
						</span>
					</span>
					<n-input
						v-model:value="yaraQuery"
						size="tiny"
						clearable
						placeholder="Filter by rule, author or ruleset"
						class="w-full sm:w-64"
					>
						<template #prefix><Icon :name="SearchIcon" :size="13" /></template>
					</n-input>
				</div>
				<div>
					<n-scrollbar style="max-height: 18rem">
						<div class="divide-border flex flex-col divide-y">
							<!-- Two zones on one baseline: the rule identity on the left, its
							     provenance right-aligned. Previously the row mixed an icon, a mono
							     name, prose ("by X") and a round tag in one wrapping flow at two
							     text sizes, so nothing lined up between rows. -->
							<div v-for="(y, i) of filteredYara" :key="i" class="flex flex-col gap-1 px-3 py-2">
								<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
									<div class="flex min-w-0 grow items-baseline gap-2">
										<Icon :name="RuleIcon" :size="13" class="text-warning shrink-0 translate-y-0.5" />
										<!-- mono: a YARA rule name is an identifier, not prose -->
										<span
											class="text-default min-w-0 truncate font-mono text-xs font-medium"
											:title="y.rule"
										>
											{{ y.rule }}
										</span>
									</div>
									<!-- Provenance as one muted run instead of a tag plus a sentence:
									     same treatment for both fields, so the right edge is uniform. -->
									<span v-if="yaraMeta(y)" class="text-tertiary shrink-0 font-mono text-2xs">
										{{ yaraMeta(y) }}
									</span>
								</div>
								<!-- Indented past the icon so it reads as belonging to the rule above. -->
								<span v-if="y.description" class="text-secondary pl-5 text-xs">
									{{ y.description }}
								</span>
							</div>
							<div v-if="!filteredYara.length" class="text-tertiary px-3 py-4 text-xs">
								No rule matches that filter.
							</div>
						</div>
					</n-scrollbar>
				</div>
			</div>

			<div v-if="intel.sigma?.length" class="border-default flex flex-col overflow-hidden rounded-lg border">
				<div class="border-default bg-secondary border-b px-4 py-2">
					<span :class="LABEL">
						Sigma matches
						<span class="text-tertiary normal-case">({{ intel.sigma.length }})</span>
					</span>
				</div>
				<n-scrollbar style="max-height: 18rem">
					<div class="divide-border flex flex-col divide-y">
						<div
							v-for="(s, i) of intel.sigma"
							:key="i"
							class="flex flex-wrap items-center gap-2 px-3 py-2 text-xs"
						>
							<n-tag size="tiny" round :bordered="false" :type="sevTag(s.level)">
								{{ s.level || "—" }}
							</n-tag>
							<span class="text-default min-w-0">{{ s.title }}</span>
							<span v-if="s.source" class="text-tertiary">· {{ s.source }}</span>
						</div>
					</div>
				</n-scrollbar>
			</div>

			<div v-if="intel.ids?.length" class="border-default flex flex-col overflow-hidden rounded-lg border">
				<div class="border-default bg-secondary border-b px-4 py-2">
					<span :class="LABEL">
						IDS/IPS alerts
						<span class="text-tertiary normal-case">({{ intel.ids.length }})</span>
					</span>
				</div>
				<n-scrollbar style="max-height: 18rem">
					<div class="divide-border flex flex-col divide-y">
						<div
							v-for="(x, i) of intel.ids"
							:key="i"
							class="flex flex-wrap items-center gap-2 px-3 py-2 text-xs"
						>
							<n-tag size="tiny" round :bordered="false" :type="sevTag(x.severity)">
								{{ x.severity || "—" }}
							</n-tag>
							<span class="text-default min-w-0 break-all">{{ x.msg }}</span>
							<span v-if="x.source" class="text-tertiary">· {{ x.source }}</span>
						</div>
					</div>
				</n-scrollbar>
			</div>

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
import { NCollapse, NCollapseItem, NEmpty, NInput, NProgress, NScrollbar, NTag } from "naive-ui"
import { computed, h, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { createFuse, searchFuse } from "@/components/common/searchDialog.helpers"
import { iconForFile } from "@/components/fileAnalysis/fileAnalysis.helpers"

const props = defineProps<{ reputation?: FileAnalysisReputation | null; loading?: boolean }>()

// Same label treatment as the summary card, so the two surfaces read as one
// design rather than two.
const LABEL = "text-secondary text-xs font-medium tracking-wider uppercase"

const BugIcon = "carbon:debug"
const RuleIcon = "carbon:rule"
const DotIcon = "carbon:circle-solid"
const SearchIcon = "carbon:search"

const intel = computed(() => props.reputation?.intel ?? null)
const permalink = computed(() => props.reputation?.permalink)

/**
 * A client-side filter over one of the report's lists. Nothing is requested as you
 * type — Fuse searches the array already delivered with the report. Fuzzy rather
 * than a substring match, so "base64" still finds "encode data using Base64" and a
 * typo in a rule name does not blank the list.
 *
 * Three lists here are long enough to need this (techniques, dropped files, YARA),
 * which is why it is a helper rather than three copies of the same two refs.
 */
function useFuseFilter<T>(source: () => T[], keys: string[]) {
	const query = ref("")
	const fuse = computed(() => createFuse(source(), keys))
	const results = computed(() => searchFuse(fuse.value, query.value, source()))
	return { query, results }
}

const { query: mitreQuery, results: filteredMitre } = useFuseFilter(
	() => intel.value?.behaviour?.mitre ?? [],
	["id", "description"]
)
const { query: droppedQuery, results: filteredDropped } = useFuseFilter(
	() => intel.value?.behaviour?.dropped_files ?? [],
	["name", "type", "sha256"]
)
const { query: yaraQuery, results: filteredYara } = useFuseFilter(() => intel.value?.yara ?? [], [
	"rule",
	"author",
	"ruleset",
	"description"
])

const detPct = computed(() => {
	const m = props.reputation?.malicious ?? 0
	const t = props.reputation?.total ?? 0
	return t > 0 ? Math.min(100, Math.round((m / t) * 100)) : 0
})
const ratioColor = computed(() => {
	const m = props.reputation?.malicious ?? 0
	if (m >= 5) return "#e88080"
	if (m >= 1) return "#e8c07d"
	return "#63e2b7"
})

const facts = computed(() => {
	const i = intel.value
	if (!i) return []
	const rows: { label: string; value: string }[] = []
	if (i.type_description) rows.push({ label: "Type", value: i.type_description })
	if (i.size != null) rows.push({ label: "Size", value: humanSize(i.size) })
	if (i.first_seen) rows.push({ label: "First seen", value: shortDate(i.first_seen) })
	if (i.last_analysis) rows.push({ label: "Last analysis", value: shortDate(i.last_analysis) })
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
function humanSize(n: number): string {
	if (!n) return "0 B"
	const u = ["B", "KB", "MB", "GB"]
	let i = 0
	let v = n
	while (v >= 1024 && i < u.length - 1) {
		v /= 1024
		i++
	}
	return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${u[i]}`
}
function shortDate(iso: string): string {
	return (iso || "").slice(0, 10)
}
function ipUrl(v: string): string {
	return `https://www.virustotal.com/gui/ip-address/${encodeURIComponent(v)}`
}
function domainUrl(v: string): string {
	return `https://www.virustotal.com/gui/domain/${encodeURIComponent(v)}`
}

// Small inline list renderer (keeps the template flat for the three-up IOC grids).
function IocList(p: { label: string; items?: string[]; link?: (v: string) => string; mono?: boolean }) {
	const items = p.items || []
	if (!items.length) return null
	// NScrollbar rather than overflow-y-auto: the native bar is a different widget
	// from the ones used everywhere else in the app, and on some platforms it only
	// appears while scrolling, so a clipped list read as truncated content.
	return h("div", { class: "flex flex-col gap-2" }, [
		h("span", { class: LABEL }, `${p.label} (${items.length})`),
		h("div", { class: "border-default rounded-lg border" }, [
			h(
				NScrollbar,
				{ style: "max-height: 13rem", class: "p-3" },
				{
					default: () =>
						h(
							"div",
							{ class: "flex flex-col gap-2" },
							items.map(it =>
								p.link
									? h(
											"a",
											{
												href: p.link(it),
												target: "_blank",
												rel: "noopener noreferrer",
												class: "hover:text-primary block py-0.5 text-xs break-all underline decoration-dotted"
											},
											it
										)
									: h("code", { class: "block py-0.5 text-xs break-all" }, it)
							)
						)
				}
			)
		])
	])
}
</script>
