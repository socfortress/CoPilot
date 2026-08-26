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

			<!-- Meaningful (sample-driven) signatures — the real signal, ranked by severity -->
			<div v-if="meaningfulSignatures.length" class="flex flex-col gap-2">
				<span :class="SECTION_LABEL">Signatures ({{ meaningfulSignatures.length }})</span>
				<div class="flex flex-col gap-2">
					<div
						v-for="(sig, i) of meaningfulSignatures"
						:key="i"
						class="bg-secondary flex items-start gap-3 rounded-lg p-3"
					>
						<Icon :name="SigIcon" :size="16" :class="sevColor(sig.severity)" class="mt-0.5 shrink-0" />
						<div class="flex grow flex-col">
							<span class="text-sm font-medium">{{ sig.name }}</span>
							<span v-if="sig.description" class="text-secondary text-xs">{{ sig.description }}</span>
						</div>
						<n-tag v-if="sig.severity" size="tiny" round :bordered="false" :type="sevTag(sig.severity)">
							sev {{ sig.severity }}
						</n-tag>
						<div class="flex flex-wrap gap-1">
							<n-tag v-for="m of sig.mitre || []" :key="m" size="tiny" round :bordered="false">
								{{ m }}
							</n-tag>
						</div>
					</div>
				</div>
			</div>

			<!-- Low-confidence static-PE / .NET-JIT heuristics — fire on legit packed/
			     signed/.NET binaries, so excluded from the verdict but shown for context. -->
			<n-collapse v-if="lowConfidenceSignatures.length">
				<n-collapse-item name="lowconf">
					<template #header>
						<span class="text-secondary text-xs">
							Static packer / .NET-JIT heuristics ({{ lowConfidenceSignatures.length }}) — fire on benign
							software, not counted toward the verdict
						</span>
					</template>
					<div class="flex flex-col gap-1 opacity-70">
						<div
							v-for="(sig, i) of lowConfidenceSignatures"
							:key="i"
							class="flex items-start gap-2 py-0.5 text-xs"
						>
							<n-tag size="tiny" round :bordered="false">sev {{ sig.severity }}</n-tag>
							<div class="flex flex-col">
								<span class="font-medium break-all">{{ sig.name }}</span>
								<span v-if="sig.description" class="text-secondary">{{ sig.description }}</span>
							</div>
						</div>
					</div>
				</n-collapse-item>
			</n-collapse>

			<!-- Environmental noise — CAPE monitor + Windows-guest baseline. Collapsed &
			     dimmed, and excluded from the verdict, so it doesn't masquerade as signal. -->
			<n-collapse v-if="noiseSignatures.length">
				<n-collapse-item name="noise">
					<template #header>
						<span class="text-secondary text-xs">
							Environmental / monitor baseline ({{ noiseSignatures.length }}) — not counted toward the
							verdict
						</span>
					</template>
					<div class="flex flex-col gap-1 opacity-60">
						<div
							v-for="(sig, i) of noiseSignatures"
							:key="i"
							class="flex items-center gap-2 py-0.5 text-xs"
						>
							<n-tag size="tiny" round :bordered="false">sev {{ sig.severity }}</n-tag>
							<span class="break-all">{{ sig.name }}</span>
						</div>
					</div>
				</n-collapse-item>
			</n-collapse>

			<!-- Process tree — children nested under parents (by ppid); the detonated
			     sample's own process is highlighted so it stands out from OS noise. -->
			<CollapsibleCard v-if="processTree.length">
				<template #header>
					<span :class="SECTION_LABEL">
						Process tree
						<span class="text-tertiary normal-case">({{ procRows.length }}/{{ processTree.length }})</span>
					</span>
					<n-tag size="tiny" round :bordered="false" type="success">
						<template #icon><Icon :name="ProcIcon" :size="11" /></template>
						sample highlighted
					</n-tag>
				</template>

				<!-- The filter lives in the body, not the header band: collapsing the card
				     should take the whole control away, and a search box above a folded list
				     is a control with nothing to act on. -->
				<div class="border-default flex flex-col border-b p-3">
					<n-input
						v-model:value="procQuery"
						size="small"
						clearable
						placeholder="Filter by process or command line"
						class="w-full sm:w-80"
					>
						<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
					</n-input>
				</div>

				<n-scrollbar style="max-height: 22rem">
					<div class="divide-border flex flex-col divide-y">
						<div
							v-for="(p, i) of procRows"
							:key="i"
							class="flex items-stretch px-3 py-2"
							:class="p.isSample ? 'bg-primary/6' : ''"
							:style="p.isSample ? { boxShadow: 'inset 2px 0 0 0 var(--primary-color)' } : {}"
						>
							<!-- Indentation is drawn as guide rails rather than left padding: at
							     depth 2+ padding alone leaves you counting pixels to work out which
							     parent a process hangs from, and the elbow says where it attaches. -->
							<!-- -my-2 bleeds the rails over the row's vertical padding, so a line runs
							     unbroken from one row into the next instead of restarting below each
							     divider and leaving every elbow detached from its parent. -->
							<span v-for="(line, d) of p.rails" :key="d" class="relative -my-2 w-4 shrink-0">
								<span v-if="line" class="bg-border absolute inset-y-0 left-2 w-px" />
							</span>
							<span v-if="p.depth" class="relative -my-2 w-4 shrink-0">
								<span
									class="bg-border absolute left-2 w-px"
									:class="p.isLast ? 'top-0 h-4' : 'inset-y-0'"
								/>
								<span class="bg-border absolute top-4 left-2 h-px w-2" />
							</span>

							<div class="flex min-w-0 grow flex-col gap-1">
								<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
									<div class="flex min-w-0 grow items-baseline gap-2">
										<Icon
											:name="ProcIcon"
											:size="13"
											class="shrink-0 translate-y-0.5"
											:class="p.isSample ? 'text-primary' : 'text-secondary'"
										/>
										<span
											class="min-w-0 truncate font-mono text-xs font-medium"
											:class="p.isSample ? 'text-primary' : 'text-default'"
											:title="p.name"
										>
											{{ p.name || "(unknown)" }}
										</span>
									</div>
									<span v-if="procMeta(p)" class="text-tertiary text-2xs shrink-0 font-mono">
										{{ procMeta(p) }}
									</span>
								</div>
								<!-- The command line sits inside the same indented column as the name,
								     so it no longer needs its own depth arithmetic to line up. -->
								<code v-if="p.command_line" class="text-secondary text-2xs break-all">
									{{ p.command_line }}
								</code>
							</div>
						</div>
						<div v-if="!procRows.length" class="text-tertiary px-3 py-4 text-xs">
							No process matches that filter.
						</div>
					</div>
				</n-scrollbar>
			</CollapsibleCard>

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
import type { SandboxSummary } from "@/types/file-analysis"
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
	NScrollbar,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, reactive, ref } from "vue"
import Api from "@/api"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { valueListParts } from "@/components/common/value-list"
import ValueList from "@/components/common/ValueList.vue"
import { useFuseFilter } from "@/components/fileAnalysis/fileAnalysis.helpers"

const props = defineProps<{
	sandbox?: SandboxSummary | null
	loading?: boolean
	dynamicStatus?: string | null
	jobId?: string
}>()

const message = useMessage()

const SearchIcon = "carbon:search"
const SigIcon = "carbon:rule"
const ProcIcon = "carbon:process"
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
			const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" })
			const url = URL.createObjectURL(blob)
			const a = document.createElement("a")
			a.href = url
			a.download = `cape-report-${props.jobId}.json`
			a.click()
			URL.revokeObjectURL(url)
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

interface TreeProc {
	name: string
	pid?: number | string
	ppid?: number | string
	command_line?: string
	depth: number
	isSample: boolean
	/** One entry per ancestor level: true where that ancestor still has siblings
	 *  below, so the guide rail must continue down through this row. */
	rails: boolean[]
	/** Last child of its parent — its elbow stops instead of running on. */
	isLast: boolean
}

// CAPE writes the submitted sample into the guest as a temp file and launches it;
// flag the process whose command line references that drop path so the real sample
// pops out from Windows' own background processes (svchost, WmiPrvSE, …).
function looksLikeSample(cmd?: string): boolean {
	if (!cmd) return false
	return /deto_|\\Temp\\|\/tmp\/|AppData\\Local\\Temp/i.test(cmd)
}

// Build a parent→child ordering from ppid. Processes whose parent isn't in the
// captured set (very common — the parent is an OS service) render as roots, so
// nothing is dropped; genuine parent/child pairs get indented under their parent.
/** pid and ppid as one muted run — both locate the process, so both read alike. */
function procMeta(p: TreeProc): string {
	return [p.pid != null ? `pid ${p.pid}` : "", p.ppid != null ? `ppid ${p.ppid}` : ""].filter(Boolean).join(" · ")
}

const processTree = computed<TreeProc[]>(() => {
	const procs = props.sandbox?.processes ?? []
	const byPid = new Map<string, (typeof procs)[number]>()
	for (const p of procs) {
		if (p.pid != null) byPid.set(String(p.pid), p)
	}

	const childrenOf = new Map<string, typeof procs>()
	const roots: typeof procs = []
	for (const p of procs) {
		const ppid = p.ppid != null ? String(p.ppid) : ""
		if (ppid && ppid !== String(p.pid) && byPid.has(ppid)) {
			const arr = childrenOf.get(ppid) ?? []
			arr.push(p)
			childrenOf.set(ppid, arr)
		} else {
			roots.push(p)
		}
	}

	const out: TreeProc[] = []
	const seen = new Set<string>()
	const walk = (p: (typeof procs)[number], depth: number, rails: boolean[], isLast: boolean) => {
		const pid = String(p.pid ?? `_${out.length}`)
		if (seen.has(pid)) return // guard against pathological ppid cycles
		seen.add(pid)
		out.push({
			name: p.name,
			pid: p.pid,
			ppid: p.ppid,
			command_line: p.command_line,
			depth,
			isSample: looksLikeSample(p.command_line),
			rails,
			isLast
		})
		// This node becomes an ancestor for its children: its rail continues past
		// them only while it still has siblings of its own left to draw.
		const kids = childrenOf.get(pid) ?? []
		kids.forEach((c, i) => walk(c, depth + 1, [...rails, !isLast], i === kids.length - 1))
	}
	roots.forEach((r, i) => walk(r, 0, [], i === roots.length - 1))
	// Any process not reached (cycle/orphan) appended flat so the count stays honest.
	for (const p of procs) {
		if (!seen.has(String(p.pid))) {
			out.push({
				name: p.name,
				pid: p.pid,
				ppid: p.ppid,
				command_line: p.command_line,
				depth: 0,
				isSample: looksLikeSample(p.command_line),
				rails: [],
				isLast: true
			})
			seen.add(String(p.pid))
		}
	}
	return out
})

const { query: procQuery, results: filteredProcesses } = useFuseFilter(
	() => processTree.value,
	["name", "command_line"]
)

// While filtering, rows are flattened: indentation that points at a parent the
// filter removed describes a tree that is not on screen.
const procRows = computed(() =>
	procQuery.value.trim()
		? filteredProcesses.value.map(p => ({ ...p, depth: 0, rails: [], isLast: true }))
		: filteredProcesses.value
)

/** name · type · full hash, in that order: the name is what you recognise, the
 *  type is what it is, the hash is what you look up — so each is toned apart
 *  rather than reading as one long grey run. */
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
const malscoreColor = computed(() => {
	const v = props.sandbox?.verdict
	if (v === "malicious") return "#e88080"
	if (v === "suspicious") return "#e8c07d"
	return "#63e2b7"
})
const verdictType = computed<"error" | "warning" | "success">(() => {
	const v = props.sandbox?.verdict
	if (v === "malicious") return "error"
	if (v === "suspicious") return "warning"
	return "success"
})

function sevColor(sev?: number): string {
	if (!sev) return "text-secondary"
	if (sev >= 3) return "text-red-500"
	if (sev >= 2) return "text-amber-500"
	return "text-secondary"
}
function sevTag(sev?: number): "error" | "warning" | "default" {
	if (!sev) return "default"
	if (sev >= 3) return "error"
	if (sev >= 2) return "warning"
	return "default"
}
</script>
