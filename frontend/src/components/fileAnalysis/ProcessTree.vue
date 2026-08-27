<template>
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
</template>

<script setup lang="ts">
/**
 * The detonated sample's process tree, filtered client-side.
 *
 * Lifted out of DetonationTab: building the tree from ppids and drawing its guide
 * rails is a self-contained job with its own edge cases (cycles, orphans, a filter
 * that flattens the hierarchy), and it was ~150 lines inside a component that
 * already carried seven other sections.
 */
import type { SandboxProcess } from "@/types/file-analysis"
import { NInput, NScrollbar, NTag } from "naive-ui"
import { computed } from "vue"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useFuseFilter } from "@/components/fileAnalysis/fileAnalysis.helpers"

const props = defineProps<{ processes?: SandboxProcess[] | null }>()

const SearchIcon = "carbon:search"
const ProcIcon = "carbon:process"

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
	const procs = props.processes ?? []
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
</script>
