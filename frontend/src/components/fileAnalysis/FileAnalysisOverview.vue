<template>
	<div v-if="result" class="border-default flex flex-col overflow-hidden rounded-lg border">
		<!-- Evidence, not the verdict: the verdict is stated once in the page header.
		     This card answers "why", starting with the reason and the second opinion. -->
		<div v-if="verdictReason || reputation || reputationPending" class="border-default border-b p-4">
			<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:gap-6">
				<div class="flex min-w-0 grow flex-col gap-1">
					<span class="text-tertiary text-2xs font-medium tracking-wider uppercase">Why this verdict</span>
					<p v-if="verdictReason" class="text-secondary m-0 text-sm">{{ verdictReason }}</p>
					<p v-else class="text-tertiary m-0 text-sm">
						Nothing stood out — no obfuscation, no flagged behaviour, no reputation hit.
					</p>
				</div>

				<!-- Second opinion sits beside the reason on wide screens and under it on
				     narrow ones, so agreement or disagreement is read in one glance. -->
				<div class="border-default flex shrink-0 flex-col gap-1 rounded-lg border p-3 lg:w-72">
					<span class="text-tertiary text-2xs font-medium tracking-wider uppercase">VirusTotal</span>
					<ReputationSummary :reputation :pending="reputationPending" />
				</div>
			</div>
		</div>

		<!-- Fact grid: one cell shape, one label style, one value style. The 1px gaps
		     read as hairlines because the container is painted the border colour and
		     each cell repaints itself — cheaper than per-cell responsive borders. -->
		<div class="grid gap-px bg-[var(--border-color)]" :class="gridClass">
			<div v-for="f in facts" :key="f.label" class="bg-secondary flex min-h-20 flex-col gap-1 p-4">
				<span class="text-tertiary text-2xs font-medium tracking-wider uppercase">{{ f.label }}</span>
				<span class="text-default text-sm break-words" :class="f.mono ? 'font-mono' : ''">{{ f.value }}</span>
			</div>
		</div>

		<!-- Hashes reuse the fact-cell language rather than inventing a third row style.
		     Hidden when empty: an incomplete analysis has none, and an empty labelled
		     band reads as a rendering fault. -->
		<div v-if="hashes.length" class="border-default flex flex-col gap-2 border-t p-4">
			<span class="text-tertiary text-2xs font-medium tracking-wider uppercase">Hashes</span>
			<div class="flex flex-col gap-1">
				<div v-for="h in hashes" :key="h.label" class="flex items-center gap-3 text-xs">
					<span class="text-tertiary w-16 shrink-0 font-mono">{{ h.label }}</span>
					<!-- span, not <code>: the global code style paints a filled bar that
					     turned each hash into a heavy band next to the flat fact cells. -->
					<span class="text-secondary min-w-0 grow truncate font-mono" :title="h.value">{{ h.value }}</span>
					<n-button text size="tiny" class="shrink-0" @click="copy(h.value)">
						<template #icon><Icon :name="CopyIcon" :size="14" /></template>
					</n-button>
				</div>
			</div>
		</div>

		<!-- Signals last: they qualify the verdict, they are not the headline. -->
		<div v-if="result.flags?.length" class="border-default flex flex-wrap items-center gap-2 border-t p-4">
			<span class="text-tertiary text-2xs font-medium tracking-wider uppercase">Signals</span>
			<n-tag
				v-for="flag of result.flags"
				:key="flag"
				:type="flag === 'analysis_incomplete' ? 'default' : 'warning'"
				size="small"
				round
				:bordered="false"
			>
				{{ flag.replaceAll("_", " ") }}
			</n-tag>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisReputation, InspectorResult } from "@/types/file-analysis"
import { NButton, NTag, useMessage } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import ReputationSummary from "@/components/fileAnalysis/ReputationSummary.vue"

const props = defineProps<{
	result?: InspectorResult | null
	reputation?: FileAnalysisReputation | null
	reputationPending?: boolean
	verdictReason?: string | null
}>()

const message = useMessage()

const CopyIcon = "carbon:copy"

const facts = computed(() => {
	const r = props.result
	if (!r) return []
	return [
		{ label: "Detected type", value: r.filetype || "unknown", mono: false },
		{ label: "Magic", value: r.magic || "—", mono: false },
		{ label: "Entropy", value: r.entropy != null ? String(r.entropy) : "—", mono: true },
		{ label: "Extension mismatch", value: r.extension_mismatch ? "yes" : "no", mono: false }
	]
})

// Four cells split evenly, but only once there is room for them to hold a value
// like the full "magic" string without wrapping into a wall.
const gridClass = computed(() => "sm:grid-cols-2 xl:grid-cols-4")

const hashes = computed(() => {
	const h = props.result?.hashes
	if (!h) return []
	return [
		{ label: "sha256", value: h.sha256 },
		{ label: "md5", value: h.md5 },
		...(h.imphash ? [{ label: "imphash", value: h.imphash }] : [])
	].filter(x => !!x.value) as { label: string; value: string }[]
})

function copy(value: string) {
	navigator.clipboard.writeText(value)
	message.success("Copied.")
}
</script>
