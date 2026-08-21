<template>
	<div class="flex flex-col gap-4">
		<n-empty
			v-if="!intel && !loading"
			description="No VirusTotal intelligence. The file is unknown to VirusTotal, or reputation is disabled."
			class="min-h-52 justify-center"
		/>

		<template v-else-if="intel">
			<!-- Headline: detection ratio + threat classification + community -->
			<div class="border-default flex flex-wrap items-center gap-6 rounded-lg border p-4">
				<div class="flex flex-col items-center gap-1">
					<n-progress type="circle" :percentage="detPct" :color="ratioColor" :style="{ width: '92px' }">
						<div class="flex flex-col items-center">
							<span class="text-lg font-semibold">{{ reputation?.malicious ?? 0 }}</span>
							<span class="text-secondary text-xs">/ {{ reputation?.total ?? "?" }}</span>
						</div>
					</n-progress>
					<span class="text-secondary text-xs">engines flagged</span>
				</div>

				<div class="flex min-w-0 flex-col gap-2">
					<div v-if="intel.threat_label" class="flex flex-wrap items-center gap-2">
						<Icon :name="BugIcon" :size="16" class="text-red-500" />
						<code class="text-base font-semibold break-all">{{ intel.threat_label }}</code>
					</div>
					<div v-else class="text-secondary text-sm">No consensus threat label.</div>
					<div v-if="intel.threat_categories?.length" class="flex flex-wrap gap-1">
						<n-tag v-for="c of intel.threat_categories" :key="c" type="error" size="small" round :bordered="false">{{ c }}</n-tag>
						<n-tag v-for="n of intel.threat_names || []" :key="n" size="small" round :bordered="false">{{ n }}</n-tag>
					</div>
				</div>

				<div class="grow" />

				<div class="text-secondary flex flex-col gap-1 text-xs">
					<div v-if="intel.reputation != null">
						Community: <span :class="intel.reputation < 0 ? 'text-red-500' : 'text-default'">{{ intel.reputation }}</span>
					</div>
					<div>
						Votes: <span class="text-green-500">{{ intel.harmless_votes ?? 0 }} harmless</span> ·
						<span class="text-red-500">{{ intel.malicious_votes ?? 0 }} malicious</span>
					</div>
					<div v-if="intel.times_submitted != null">Submitted {{ intel.times_submitted }}×</div>
				</div>
			</div>

			<!-- File facts -->
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<div v-for="f in facts" :key="f.label" class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<span class="text-secondary text-xs">{{ f.label }}</span>
					<span class="text-sm font-medium break-all">{{ f.value }}</span>
				</div>
			</div>

			<!-- VT sandbox behaviour — the detonation stand-in when our own sandbox is offline -->
			<div v-if="intel.behaviour" class="border-default flex flex-col gap-3 rounded-lg border p-4">
				<div class="flex flex-wrap items-center gap-2">
					<Icon :name="SandboxIcon" :size="16" class="text-primary" />
					<span class="text-sm font-semibold">Behaviour observed by VirusTotal's sandboxes</span>
					<n-tag size="tiny" round :bordered="false" type="info">no local detonation needed</n-tag>
				</div>

				<div v-if="intel.behaviour.mitre?.length" class="flex flex-col gap-1">
					<span class="text-secondary text-xs font-medium">MITRE ATT&CK</span>
					<div class="flex flex-wrap gap-2">
						<n-tag v-for="t of intel.behaviour.mitre" :key="t.id" type="warning" size="small" round :bordered="false">
							{{ t.id }}<span v-if="t.description" class="opacity-70"> · {{ t.description }}</span>
						</n-tag>
					</div>
				</div>

				<div class="grid gap-3 md:grid-cols-3">
					<IocList label="Contacted IPs" :items="intel.behaviour.contacted_ips" :link="ipUrl" />
					<IocList label="Contacted domains" :items="intel.behaviour.contacted_domains" :link="domainUrl" />
					<IocList label="Contacted URLs" :items="intel.behaviour.contacted_urls" />
				</div>

				<div v-if="intel.behaviour.dropped_files?.length" class="flex flex-col gap-1">
					<span class="text-secondary text-xs font-medium">Dropped files ({{ intel.behaviour.dropped_files.length }})</span>
					<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
						<div v-for="(d, i) of intel.behaviour.dropped_files" :key="i" class="flex items-center gap-2 text-xs">
							<span class="font-medium break-all">{{ d.name || "(unnamed)" }}</span>
							<n-tag v-if="d.type" size="tiny" round :bordered="false">{{ d.type }}</n-tag>
							<code v-if="d.sha256" class="text-secondary break-all">{{ d.sha256.slice(0, 20) }}</code>
						</div>
					</div>
				</div>

				<div class="grid gap-3 md:grid-cols-3">
					<IocList label="Processes" :items="intel.behaviour.processes" mono />
					<IocList label="Registry keys" :items="intel.behaviour.registry_keys" mono />
					<IocList label="Mutexes" :items="intel.behaviour.mutexes" mono />
				</div>
			</div>

			<!-- Crowdsourced detection rules -->
			<div v-if="intel.yara?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Crowdsourced YARA ({{ intel.yara.length }})</span>
				<div class="flex flex-col gap-2">
					<div v-for="(y, i) of intel.yara" :key="i" class="bg-secondary flex flex-col gap-0.5 rounded-lg p-3">
						<div class="flex flex-wrap items-center gap-2 text-sm">
							<Icon :name="RuleIcon" :size="14" class="text-amber-500" />
							<span class="font-medium">{{ y.rule }}</span>
							<span v-if="y.author" class="text-secondary text-xs">by {{ y.author }}</span>
							<n-tag v-if="y.ruleset" size="tiny" round :bordered="false">{{ y.ruleset }}</n-tag>
						</div>
						<span v-if="y.description" class="text-secondary text-xs">{{ y.description }}</span>
					</div>
				</div>
			</div>

			<div v-if="intel.sigma?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Sigma matches ({{ intel.sigma.length }})</span>
				<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<div v-for="(s, i) of intel.sigma" :key="i" class="flex flex-wrap items-center gap-2 text-xs">
						<n-tag size="tiny" round :bordered="false" :type="sevTag(s.level)">{{ s.level || "—" }}</n-tag>
						<span class="font-medium">{{ s.title }}</span>
						<span v-if="s.source" class="text-secondary">· {{ s.source }}</span>
					</div>
				</div>
			</div>

			<div v-if="intel.ids?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">IDS/IPS alerts ({{ intel.ids.length }})</span>
				<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<div v-for="(x, i) of intel.ids" :key="i" class="flex flex-wrap items-center gap-2 text-xs">
						<n-tag size="tiny" round :bordered="false" :type="sevTag(x.severity)">{{ x.severity || "—" }}</n-tag>
						<span class="font-medium break-all">{{ x.msg }}</span>
						<span v-if="x.source" class="text-secondary">· {{ x.source }}</span>
					</div>
				</div>
			</div>

			<!-- Per-engine detections (collapsed by default; can be long) -->
			<n-collapse v-if="intel.detections?.length">
				<n-collapse-item :title="`Engine detections (${intel.detection_count ?? intel.detections.length})`" name="det">
					<n-scrollbar class="bg-secondary max-h-80 rounded-lg p-3">
						<div v-for="(d, i) of intel.detections" :key="i" class="flex items-center gap-2 py-0.5 text-xs">
							<Icon
								:name="DotIcon"
								:size="10"
								:class="d.category === 'malicious' ? 'text-red-500' : 'text-amber-500'"
							/>
							<span class="w-40 shrink-0 font-medium">{{ d.engine }}</span>
							<code class="break-all">{{ d.result }}</code>
						</div>
					</n-scrollbar>
				</n-collapse-item>
			</n-collapse>

			<div class="flex items-center gap-3 text-xs">
				<a v-if="permalink" :href="permalink" target="_blank" rel="noopener noreferrer" class="hover:text-primary underline">
					Full report on VirusTotal ↗
				</a>
				<span class="text-secondary">VirusTotal aggregates 70+ engines and multiple community sandboxes — treat it as corroboration, not ground truth.</span>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisReputation } from "@/types/file-analysis"
import { NCollapse, NCollapseItem, NEmpty, NProgress, NScrollbar, NTag } from "naive-ui"
import { computed, h } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ reputation?: FileAnalysisReputation | null; loading?: boolean }>()

const BugIcon = "carbon:bug"
const SandboxIcon = "carbon:play-filled-alt"
const RuleIcon = "carbon:rule"
const DotIcon = "carbon:circle-solid"

const intel = computed(() => props.reputation?.intel ?? null)
const permalink = computed(() => props.reputation?.permalink)

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
const IocList = (p: { label: string; items?: string[]; link?: (v: string) => string; mono?: boolean }) => {
	const items = p.items || []
	if (!items.length) return null
	return h("div", { class: "flex flex-col gap-1" }, [
		h("span", { class: "text-secondary text-xs font-medium" }, `${p.label} (${items.length})`),
		h(
			"div",
			{ class: "bg-secondary flex max-h-52 flex-col gap-1 overflow-y-auto rounded-lg p-3" },
			items.map(it =>
				p.link
					? h(
							"a",
							{
								href: p.link(it),
								target: "_blank",
								rel: "noopener noreferrer",
								class: "hover:text-primary text-xs break-all underline decoration-dotted"
							},
							it
						)
					: h("code", { class: `text-xs break-all${p.mono ? "" : ""}` }, it)
			)
		)
	])
}
</script>
