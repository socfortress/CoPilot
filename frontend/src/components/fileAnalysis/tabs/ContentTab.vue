<template>
	<div class="flex flex-col gap-4">
		<n-empty
			v-if="!hasAnyContent && !loading"
			description="No extracted content yet."
			class="min-h-52 justify-center"
		/>

		<!-- Signals: same name the summary card gives these flags, and the same
		     label-above-tags shape as the other tag groups on this tab. A bare row of
		     tags did not say what they were. -->
		<div v-if="result?.flags?.length" class="flex flex-col gap-2">
			<span :class="LABEL">Signals</span>
			<div class="flex flex-wrap items-center gap-2">
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

		<!-- Scripts: raw + deobfuscated side by side -->
		<div v-if="content.raw" class="grid gap-3 lg:grid-cols-2">
			<CodeBlock title="Raw source" :code="content.raw" />
			<CodeBlock
				title="Deobfuscated (static — not executed)"
				:code="content.deobfuscated"
				empty-text="— no obfuscation unwound —"
			/>
		</div>

		<!-- Macro source -->
		<div v-if="content.macros" class="flex flex-col gap-2">
			<div v-if="content.autoexec_keywords?.length" class="flex flex-col gap-2">
				<span :class="LABEL">Auto-exec triggers</span>
				<div class="flex flex-wrap gap-2">
					<n-tag
						v-for="k of content.autoexec_keywords"
						:key="k"
						type="error"
						size="small"
						round
						:bordered="false"
					>
						{{ k }}
					</n-tag>
				</div>
			</div>
			<CodeBlock title="Macro source (VBA)" :code="content.macros" />
		</div>

		<!-- Embedded PDF JavaScript -->
		<CodeBlock
			v-if="content.javascript"
			title="Embedded PDF JavaScript (extracted, not executed)"
			:code="content.javascript"
		/>

		<!-- Extracted document text (PDF visible text) -->
		<CodeBlock v-if="content.text" title="Extracted text" :code="content.text" />

		<!-- Shortcut target: label/value rows in a card, matching the other detail
		     surfaces. Inline "Target:" + <code> put the label and the path on one
		     baseline at two different treatments, so nothing lined up between rows. -->
		<div
			v-if="content.arguments || content.target"
			class="border-default flex flex-col overflow-hidden rounded-lg border"
		>
			<div class="border-default bg-secondary border-b px-4 py-2">
				<span :class="LABEL">Shortcut target</span>
			</div>
			<div class="divide-border flex flex-col divide-y">
				<div v-for="row of lnkRows" :key="row.label" class="flex flex-wrap items-baseline gap-x-3 px-4 py-2">
					<span class="text-tertiary w-28 shrink-0 font-mono text-xs">{{ row.label }}</span>
					<span class="text-default min-w-0 font-mono text-xs break-all">{{ row.value }}</span>
				</div>
			</div>
		</div>

		<!-- PE capabilities -->
		<div v-if="content.capabilities?.length" class="flex flex-col gap-2">
			<span :class="LABEL">Capabilities (capa)</span>
			<div class="flex flex-wrap gap-2">
				<n-tag v-for="c of content.capabilities" :key="c" size="small" round :bordered="false">{{ c }}</n-tag>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { InspectorContent, InspectorResult } from "@/types/file-analysis"
import { NEmpty, NTag } from "naive-ui"
import { computed } from "vue"
import CodeBlock from "../CodeBlock.vue"

const props = defineProps<{ result?: InspectorResult | null; loading?: boolean }>()

// Same label treatment as the summary card and the other tabs, so the module
// reads as one design rather than a per-tab decision.
const LABEL = "text-secondary text-xs font-medium tracking-wider uppercase"

const content = computed<InspectorContent>(() => props.result?.content ?? {})

const lnkRows = computed(() =>
	[
		{ label: "target", value: content.value.target },
		{ label: "arguments", value: content.value.arguments },
		{ label: "working dir", value: content.value.working_dir },
		{ label: "icon", value: content.value.icon_location }
	].filter((r): r is { label: string; value: string } => Boolean(r.value))
)

const hasAnyContent = computed(() =>
	Boolean(
		content.value.raw ||
		content.value.macros ||
		content.value.javascript ||
		content.value.text ||
		content.value.arguments ||
		content.value.target ||
		content.value.capabilities?.length
	)
)
</script>
