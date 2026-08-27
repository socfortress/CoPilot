<template>
	<div class="@container flex flex-col gap-4">
		<!-- States when there's no report yet -->
		<n-spin v-if="!sandbox && dynamicStatus === 'running'" show class="min-h-52">
			<div class="flex min-h-52 flex-col items-center justify-center gap-2">
				<span class="text-sm font-medium">Detonating in the sandbox…</span>
				<span class="text-secondary text-xs">
					Dynamic analysis runs over minutes — this fills in when the report lands.
				</span>
			</div>
		</n-spin>

		<n-alert v-else-if="!sandbox && dynamicStatus === 'failed'" type="warning" :bordered="false">
			<template #header>Detonation didn't complete</template>
			The sandbox couldn't produce a report for this sample. The most common cause is a
			<b>platform mismatch</b>
			— e.g. a Windows PE/PowerShell/Office file with only a Linux guest available (or vice-versa). The static
			analysis above is still valid.
		</n-alert>

		<n-empty
			v-else-if="!sandbox && !loading"
			description="No detonation report. This file type wasn't escalated to the sandbox, or detonation is disabled."
			class="min-h-52 justify-center"
		/>

		<template v-else-if="sandbox">
			<!-- Headline: score + verdict + run facts -->
			<!-- Headline as three hairline-separated cells, matching the VirusTotal tab:
			     score, verdict and run facts read as three answers instead of a row of
			     controls pushed apart by a grow spacer. -->
			<div
				class="border-default bg-border grid gap-px overflow-hidden rounded-lg border @4xl:grid-cols-[auto_1fr_auto]"
			>
				<div class="bg-secondary flex items-center gap-4 p-4">
					<n-progress
						type="circle"
						:percentage="malscorePct"
						:color="malscoreColor"
						:style="{ width: '76px' }"
					>
						<span class="text-lg leading-none font-semibold">{{ sandbox.malscore.toFixed(1) }}</span>
					</n-progress>
					<div class="flex flex-col gap-1">
						<span :class="SECTION_LABEL">Malscore</span>
						<span class="text-secondary text-xs">out of 10</span>
					</div>
				</div>

				<div class="bg-secondary flex min-w-0 flex-col gap-2 p-4">
					<span :class="SECTION_LABEL">Verdict</span>
					<!-- Both tags at one size: verdict and family are two facts about the
					     same run, and a taller verdict next to a shorter family read as a
					     control beside a label rather than as a pair. -->
					<div class="flex flex-wrap items-center gap-2">
						<n-tag :type="verdictType" size="medium" round :bordered="false" class="capitalize">
							{{ sandbox.verdict || "clean" }}
						</n-tag>
						<n-tag v-if="sandbox.family" type="error" size="medium" round :bordered="false">
							{{ sandbox.family }}
						</n-tag>
					</div>
				</div>

				<!-- Run facts as aligned label/value rows: they used to run on as prose
				     ("Guest: capewin"), which buried the values. -->
				<div class="bg-secondary flex flex-col gap-2 p-4 @4xl:w-60">
					<span :class="SECTION_LABEL">Run</span>
					<div class="flex flex-col gap-1 text-xs">
						<div v-if="sandbox.machine" class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">guest</span>
							<span class="text-secondary min-w-0 truncate font-mono">{{ sandbox.machine }}</span>
						</div>
						<div v-if="sandbox.duration" class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">duration</span>
							<span class="text-secondary font-mono tabular-nums">{{ sandbox.duration }}s</span>
						</div>
						<div v-if="sandbox.task_id != null" class="flex items-baseline justify-between gap-3">
							<span class="text-tertiary">CAPE task</span>
							<span class="text-secondary font-mono tabular-nums">#{{ sandbox.task_id }}</span>
						</div>
					</div>
				</div>
			</div>

			<!-- MITRE ATT&CK -->
			<div v-if="sandbox.ttps?.length" class="flex flex-col gap-2">
				<span :class="SECTION_LABEL">MITRE ATT&CK</span>
				<div class="flex flex-wrap gap-2">
					<!-- Composite key: a technique id repeats across tactics, so it is not unique. -->
					<n-tag
						v-for="(t, ti) of sandbox.ttps"
						:key="`${t.id}-${ti}`"
						type="warning"
						size="small"
						round
						:bordered="false"
					>
						{{ t.id }}
						<span v-if="t.signature" class="opacity-70">· {{ t.signature }}</span>
					</n-tag>
				</div>
			</div>

			<!-- The real signal, ranked by severity -->
			<SignatureList v-if="meaningfulSignatures.length" :signatures="meaningfulSignatures" label="Signatures" />

			<!-- Fire on legitimately packed / signed / .NET binaries, so they are shown for
			     context but kept out of the verdict. -->
			<SignatureList
				v-if="lowConfidenceSignatures.length"
				:signatures="lowConfidenceSignatures"
				label="Static packer / .NET-JIT heuristics"
				variant="secondary"
				note="fire on benign software, not counted toward the verdict"
			/>

			<!-- CAPE monitor + Windows-guest baseline: fires on every run, sample or not. -->
			<SignatureList
				v-if="noiseSignatures.length"
				:signatures="noiseSignatures"
				label="Environmental / monitor baseline"
				variant="secondary"
			/>

			<ProcessTree :processes="sandbox.processes" />

			<!-- Extracted payloads and dropped files are one-line facts about a file —
			     name, type, hash — so they use the module's shared list rather than each
			     inventing its own row. The full sha256 is kept: a truncated hash cannot be
			     looked up anywhere. -->
			<ValueList
				v-if="sandbox.payloads?.length"
				label="Extracted payloads"
				:items="payloadItems"
				max-height="18rem"
			/>

			<ValueList v-if="sandbox.dropped?.length" label="Dropped files" :items="droppedItems" max-height="18rem" />

			<!-- Host activity — the FULL behavioural record (judge from evidence, not the score) -->
			<div
				v-if="behaviorGroups.length || sandbox.enhanced?.length || sandbox.dead_hosts?.length"
				class="flex flex-col gap-2"
			>
				<div class="flex items-center justify-between">
					<span :class="SECTION_LABEL">Host activity — everything the sample did</span>
					<n-button v-if="jobId" text size="tiny" :loading="downloadingReport" @click="downloadReport">
						<template #icon><Icon :name="DownloadIcon" :size="14" /></template>
						Raw CAPE JSON (advanced)
					</n-button>
				</div>

				<n-alert
					v-if="sandbox.dead_hosts?.length"
					type="warning"
					size="small"
					:bordered="false"
					class="mb-2 text-xs"
				>
					Tried to reach (unreachable):
					<code v-for="(h, i) of sandbox.dead_hosts" :key="i" class="mr-2 break-all">{{ h }}</code>
				</n-alert>

				<n-collapse>
					<n-collapse-item
						v-for="g of behaviorGroups"
						:key="g.key"
						:name="g.key"
						:title="`${g.label} (${g.items.length})`"
					>
						<n-input
							v-if="g.items.length > 20"
							v-model:value="filters[g.key]"
							size="tiny"
							clearable
							placeholder="Filter…"
							class="mb-2"
						/>
						<ValueList :items="filtered(g)" max-height="18rem" empty-text="No matches." />
					</n-collapse-item>

					<n-collapse-item
						v-if="sandbox.enhanced?.length"
						name="_timeline"
						:title="`Behaviour timeline (${sandbox.enhanced.length} events)`"
					>
						<ValueList :items="timelineItems" max-height="24rem" />
					</n-collapse-item>

					<!-- CAPE errors (diagnostics) -->
					<n-collapse-item
						v-if="sandbox.errors?.length"
						:title="`Sandbox diagnostics (${sandbox.errors.length})`"
						name="err"
					>
						<ValueList :items="sandbox.errors" max-height="13rem" />
					</n-collapse-item>
				</n-collapse>
			</div>

			<!-- Screenshots -->
			<div v-if="sandbox.screenshots?.length" class="flex flex-col gap-2">
				<span :class="SECTION_LABEL">Screenshots</span>
				<n-image-group>
					<div class="flex flex-wrap gap-2">
						<n-image
							v-for="(s, i) of sandbox.screenshots"
							:key="i"
							:src="s"
							width="160"
							class="rounded-lg"
						/>
					</div>
				</n-image-group>
			</div>

			<div class="text-secondary text-xs">
				"Nothing malicious observed" isn't a guarantee — a sample may detect the sandbox or wait. Weigh it with
				the static + reputation signals.
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisVerdict, SandboxSummary } from "@/types/file-analysis"
import { saveAs } from "file-saver"
import {
	NAlert,
	NButton,
	NCollapse,
	NCollapseItem,
	NEmpty,
	NImage,
	NImageGroup,
	NInput,
	NProgress,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { valueListParts } from "@/components/common/value-list"
import ValueList from "@/components/common/ValueList.vue"
import { verdictColorVar, verdictTagType } from "@/components/fileAnalysis/fileAnalysis.helpers"
import ProcessTree from "@/components/fileAnalysis/ProcessTree.vue"
import SignatureList from "@/components/fileAnalysis/SignatureList.vue"

const props = defineProps<{
	sandbox?: SandboxSummary | null
	loading?: boolean
	dynamicStatus?: string | null
	jobId?: string
}>()

const message = useMessage()

const DownloadIcon = "carbon:download"

// The full host-activity record, grouped for display. Labels are analyst-facing;
// order puts the highest-signal categories (writes/deletes/commands) first.
const _BEHAVIOR_LABELS: { key: string; label: string }[] = [
	{ key: "executed_commands", label: "Executed commands" },
	{ key: "created_services", label: "Services created" },
	{ key: "started_services", label: "Services started" },
	{ key: "write_files", label: "Files written" },
	{ key: "delete_files", label: "Files deleted" },
	{ key: "write_keys", label: "Registry written" },
	{ key: "delete_keys", label: "Registry deleted" },
	{ key: "files", label: "Files touched" },
	{ key: "read_files", label: "Files read" },
	{ key: "registry_keys", label: "Registry keys touched" },
	{ key: "read_keys", label: "Registry keys read" },
	{ key: "mutexes", label: "Mutexes" },
	{ key: "resolved_apis", label: "Resolved APIs" }
]

const behaviorGroups = computed(() => {
	const b = props.sandbox?.behavior ?? {}
	return _BEHAVIOR_LABELS.map(({ key, label }) => ({ key, label, items: b[key] ?? [] })).filter(g => g.items.length)
})

const filters = reactive<Record<string, string>>({})

function filtered(g: { key: string; items: string[] }): string[] {
	const q = (filters[g.key] || "").toLowerCase().trim()
	return q ? g.items.filter(it => it.toLowerCase().includes(q)) : g.items
}

/** One timeline row: what happened, what it happened to, and the call detail. */
const timelineItems = computed(() =>
	(props.sandbox?.enhanced ?? []).map(ev =>
		valueListParts([
			{ text: ev.event, tone: "accent" },
			{ text: ev.object, tone: "strong" },
			{ text: eventDetail(ev), tone: "muted" }
		])
	)
)

function eventDetail(ev: { data?: Record<string, unknown> }): string {
	const d = ev.data
	if (!d || typeof d !== "object") return ""
	const parts = Object.entries(d)
		.filter(([, v]) => v != null && v !== "")
		.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`)

	if (parts.length === 0) return "—"
	return parts.join("  ")
}

const downloadingReport = ref(false)
function downloadReport() {
	if (!props.jobId || downloadingReport.value) return
	downloadingReport.value = true
	Api.fileAnalysis
		.getCapeReport(props.jobId)
		.then(res => {
			saveAs(
				new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" }),
				`cape-report-${props.jobId}.json`
			)
		})
		.catch(() => message.error("Could not fetch the full CAPE report."))
		.finally(() => {
			downloadingReport.value = false
		})
}

// Split real signal from environmental noise (CAPE-monitor/Windows baseline). The
// backend tags each signature; noise is shown separately so a malscore-10 benign
// run reads clearly instead of a wall of scary-looking sev-2/3 hits.
const _bySeverity = (a: { severity?: number }, b: { severity?: number }) => (b.severity ?? 0) - (a.severity ?? 0)
const meaningfulSignatures = computed(() =>
	(props.sandbox?.signatures ?? []).filter(s => !s.noise && !s.low_confidence).sort(_bySeverity)
)
const lowConfidenceSignatures = computed(() =>
	(props.sandbox?.signatures ?? []).filter(s => s.low_confidence && !s.noise).sort(_bySeverity)
)
const noiseSignatures = computed(() => (props.sandbox?.signatures ?? []).filter(s => s.noise).sort(_bySeverity))

function fileLine(f: { name?: string; type?: string; sha256?: string }) {
	return valueListParts([
		{ text: f.name, tone: "strong" },
		{ text: f.type, tone: "accent" },
		{ text: f.sha256, tone: "muted" }
	])
}

const payloadItems = computed(() => (props.sandbox?.payloads ?? []).map(fileLine))
const droppedItems = computed(() => (props.sandbox?.dropped ?? []).map(fileLine))

const malscorePct = computed(() => Math.min(100, Math.max(0, (props.sandbox?.malscore ?? 0) * 10)))
// Colour the ring by the VERDICT, not the raw malscore — a benign run can hit
// malscore 10 on environmental noise, and a red ring next to a "clean" tag misleads.
// The sandbox summary types its verdict as a free string (it mirrors CAPE's own
// wording), so it is narrowed here instead of loosening the shared helpers.
const sandboxVerdict = computed<FileAnalysisVerdict>(() => {
	const v = props.sandbox?.verdict
	return v === "malicious" || v === "suspicious" ? v : "clean"
})

// Colour the ring by the VERDICT, not the raw malscore — a benign run can hit
// malscore 10 on environmental noise, and a red ring next to a "clean" tag misleads.
const malscoreColor = computed(() => verdictColorVar(sandboxVerdict.value))
const verdictType = computed(() => verdictTagType(sandboxVerdict.value))
</script>
