<template>
	<div class="flex flex-col gap-4">
		<!-- States when there's no report yet -->
		<n-spin v-if="!sandbox && dynamicStatus === 'running'" show class="min-h-52">
			<div class="flex min-h-52 flex-col items-center justify-center gap-2">
				<span class="text-sm font-medium">Detonating in the sandbox…</span>
				<span class="text-secondary text-xs">Dynamic analysis runs over minutes — this fills in when the report lands.</span>
			</div>
		</n-spin>

		<n-alert v-else-if="!sandbox && dynamicStatus === 'failed'" type="warning" :bordered="false">
			<template #header>Detonation didn't complete</template>
			The sandbox couldn't produce a report for this sample. The most common cause is a
			<b>platform mismatch</b> — e.g. a Windows PE/PowerShell/Office file with only a Linux guest available (or vice-versa).
			The static analysis above is still valid.
		</n-alert>

		<n-empty
			v-else-if="!sandbox && !loading"
			description="No detonation report. This file type wasn't escalated to the sandbox, or detonation is disabled."
			class="min-h-52 justify-center"
		/>

		<template v-else-if="sandbox">
			<!-- Headline: score + verdict + run facts -->
			<div class="border-default flex flex-wrap items-center gap-6 rounded-lg border p-4">
				<div class="flex flex-col items-center gap-1">
					<n-progress type="circle" :percentage="malscorePct" :color="malscoreColor" :style="{ width: '92px' }">
						<span class="text-lg font-semibold">{{ sandbox.malscore.toFixed(1) }}</span>
					</n-progress>
					<span class="text-secondary text-xs">malscore / 10</span>
				</div>
				<div class="flex flex-col gap-2">
					<n-tag :type="verdictType" size="large" round :bordered="false" class="capitalize">
						{{ sandbox.verdict || "clean" }}
					</n-tag>
					<n-tag v-if="sandbox.family" type="error" size="small" round :bordered="false">{{ sandbox.family }}</n-tag>
				</div>
				<div class="grow" />
				<div class="text-secondary flex flex-col gap-1 text-xs">
					<div v-if="sandbox.machine">Guest: <span class="text-default">{{ sandbox.machine }}</span></div>
					<div v-if="sandbox.duration">Duration: <span class="text-default">{{ sandbox.duration }}s</span></div>
					<div v-if="sandbox.task_id != null">CAPE task: <span class="text-default">#{{ sandbox.task_id }}</span></div>
				</div>
			</div>

			<!-- MITRE ATT&CK -->
			<div v-if="sandbox.ttps?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">MITRE ATT&CK</span>
				<div class="flex flex-wrap gap-2">
					<n-tag v-for="t of sandbox.ttps" :key="t.id" type="warning" size="small" round :bordered="false">
						{{ t.id }}<span v-if="t.signature" class="opacity-70"> · {{ t.signature }}</span>
					</n-tag>
				</div>
			</div>

			<!-- Signatures (ordered by severity, most severe first) -->
			<div v-if="sortedSignatures.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Signatures ({{ sortedSignatures.length }})</span>
				<div class="flex flex-col gap-2">
					<div v-for="(sig, i) of sortedSignatures" :key="i" class="bg-secondary flex items-start gap-3 rounded-lg p-3">
						<Icon :name="SigIcon" :size="16" :class="sevColor(sig.severity)" class="mt-0.5 shrink-0" />
						<div class="flex grow flex-col">
							<span class="text-sm font-medium">{{ sig.name }}</span>
							<span v-if="sig.description" class="text-secondary text-xs">{{ sig.description }}</span>
						</div>
						<n-tag v-if="sig.severity" size="tiny" round :bordered="false" :type="sevTag(sig.severity)">
							sev {{ sig.severity }}
						</n-tag>
						<div class="flex flex-wrap gap-1">
							<n-tag v-for="m of sig.mitre || []" :key="m" size="tiny" round :bordered="false">{{ m }}</n-tag>
						</div>
					</div>
				</div>
			</div>

			<!-- Process tree — children nested under parents (by ppid); the detonated
			     sample's own process is highlighted so it stands out from OS noise. -->
			<div v-if="processTree.length" class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<span class="text-secondary text-xs font-medium">Process tree ({{ processTree.length }})</span>
					<n-tag size="tiny" round :bordered="false" type="success">
						<template #icon><Icon :name="ProcIcon" :size="11" /></template>
						sample highlighted
					</n-tag>
				</div>
				<n-scrollbar class="bg-secondary max-h-80 rounded-lg p-3">
					<div
						v-for="(p, i) of processTree"
						:key="i"
						class="flex flex-col border-b border-[var(--n-border-color)] py-1 last:border-0"
						:style="p.isSample
							? {
								borderLeft: '2px solid var(--primary-color)',
								background: 'color-mix(in srgb, var(--primary-color) 7%, transparent)',
								borderRadius: '4px'
							}
							: {}"
					>
						<div class="flex items-center gap-2 text-sm" :style="{ paddingLeft: `${p.depth * 18}px` }">
							<span v-if="p.depth" class="text-secondary select-none">└</span>
							<Icon :name="ProcIcon" :size="14" :class="p.isSample ? 'text-primary' : 'text-secondary'" />
							<span class="font-medium" :class="p.isSample ? 'text-primary' : ''">{{ p.name || "(unknown)" }}</span>
							<span v-if="p.pid != null || p.ppid != null" class="text-secondary text-xs">
								<span v-if="p.pid != null">pid {{ p.pid }}</span>
								<span v-if="p.pid != null && p.ppid != null"> · </span>
								<span v-if="p.ppid != null">ppid {{ p.ppid }}</span>
							</span>
							<n-tag v-if="p.isSample" size="tiny" round :bordered="false" type="success">sample</n-tag>
						</div>
						<code
							v-if="p.command_line"
							class="text-secondary text-xs break-all"
							:style="{ paddingLeft: `${p.depth * 18 + 22}px` }"
						>{{ p.command_line }}</code>
					</div>
				</n-scrollbar>
			</div>

			<!-- Extracted payloads -->
			<div v-if="sandbox.payloads?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Extracted payloads ({{ sandbox.payloads.length }})</span>
				<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<div v-for="(p, i) of sandbox.payloads" :key="i" class="flex items-center gap-2 text-xs">
						<n-tag v-if="p.type" size="tiny" round :bordered="false" type="info">{{ p.type }}</n-tag>
						<span class="font-medium">{{ p.name }}</span>
						<code class="text-secondary break-all">{{ p.sha256.slice(0, 24) }}</code>
					</div>
				</div>
			</div>

			<!-- Dropped files -->
			<div v-if="sandbox.dropped?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Dropped files ({{ sandbox.dropped.length }})</span>
				<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
					<div v-for="(d, i) of sandbox.dropped" :key="i" class="flex items-center gap-2 text-xs">
						<span v-if="d.name" class="font-medium">{{ d.name }}</span>
						<n-tag v-if="d.type" size="tiny" round :bordered="false">{{ d.type }}</n-tag>
						<code class="text-secondary break-all">{{ d.sha256.slice(0, 24) }}</code>
					</div>
				</div>
			</div>

			<!-- Screenshots -->
			<div v-if="sandbox.screenshots?.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">Screenshots</span>
				<n-image-group>
					<div class="flex flex-wrap gap-2">
						<n-image v-for="(s, i) of sandbox.screenshots" :key="i" :src="s" width="160" class="rounded-lg" />
					</div>
				</n-image-group>
			</div>

			<!-- CAPE errors (diagnostics) -->
			<n-collapse v-if="sandbox.errors?.length">
				<n-collapse-item :title="`Sandbox diagnostics (${sandbox.errors.length})`" name="err">
					<n-scrollbar class="bg-secondary max-h-52 rounded-lg p-3">
						<code v-for="(e, i) of sandbox.errors" :key="i" class="block text-xs break-all">{{ e }}</code>
					</n-scrollbar>
				</n-collapse-item>
			</n-collapse>

			<div class="text-secondary text-xs">
				"Nothing malicious observed" isn't a guarantee — a sample may detect the sandbox or wait. Weigh it with the static +
				reputation signals.
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { SandboxSummary } from "@/types/file-analysis"
import {
	NAlert,
	NCollapse,
	NCollapseItem,
	NEmpty,
	NImage,
	NImageGroup,
	NProgress,
	NScrollbar,
	NSpin,
	NTag
} from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ sandbox?: SandboxSummary | null; loading?: boolean; dynamicStatus?: string | null }>()

const SigIcon = "carbon:rule"
const ProcIcon = "carbon:process"

// Signatures ranked most-severe first — an analyst reads top-down, so the sev-3
// hits shouldn't be buried under a dozen sev-1 environmental checks.
const sortedSignatures = computed(() =>
	[...(props.sandbox?.signatures ?? [])].sort((a, b) => (b.severity ?? 0) - (a.severity ?? 0))
)

interface TreeProc {
	name: string
	pid?: number | string
	ppid?: number | string
	command_line?: string
	depth: number
	isSample: boolean
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
const processTree = computed<TreeProc[]>(() => {
	const procs = props.sandbox?.processes ?? []
	const byPid = new Map<string, (typeof procs)[number]>()
	for (const p of procs) if (p.pid != null) byPid.set(String(p.pid), p)

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
	const walk = (p: (typeof procs)[number], depth: number) => {
		const pid = String(p.pid ?? `_${out.length}`)
		if (seen.has(pid)) return // guard against pathological ppid cycles
		seen.add(pid)
		out.push({
			name: p.name,
			pid: p.pid,
			ppid: p.ppid,
			command_line: p.command_line,
			depth,
			isSample: looksLikeSample(p.command_line)
		})
		for (const c of childrenOf.get(pid) ?? []) walk(c, depth + 1)
	}
	for (const r of roots) walk(r, 0)
	// Any process not reached (cycle/orphan) appended flat so the count stays honest.
	for (const p of procs) {
		if (!seen.has(String(p.pid))) {
			out.push({
				name: p.name,
				pid: p.pid,
				ppid: p.ppid,
				command_line: p.command_line,
				depth: 0,
				isSample: looksLikeSample(p.command_line)
			})
			seen.add(String(p.pid))
		}
	}
	return out
})

const malscorePct = computed(() => Math.min(100, Math.max(0, (props.sandbox?.malscore ?? 0) * 10)))
const malscoreColor = computed(() => {
	const s = props.sandbox?.malscore ?? 0
	if (s >= 7) return "#e88080"
	if (s >= 3) return "#e8c07d"
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
