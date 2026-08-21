<template>
	<div class="flex flex-col gap-4">
		<n-empty v-if="!hasAnyContent && !loading" description="No extracted content yet." class="min-h-52 justify-center" />

		<!-- Flags row -->
		<div v-if="result?.flags?.length" class="flex flex-wrap items-center gap-2">
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
			<div v-if="content.autoexec_keywords?.length" class="flex flex-wrap gap-2">
				<span class="text-secondary text-xs">Auto-exec:</span>
				<n-tag v-for="k of content.autoexec_keywords" :key="k" type="error" size="tiny" round :bordered="false">
					{{ k }}
				</n-tag>
			</div>
			<CodeBlock title="Macro source (VBA)" :code="content.macros" />
		</div>

		<!-- Embedded PDF JavaScript -->
		<CodeBlock v-if="content.javascript" title="Embedded PDF JavaScript (extracted, not executed)" :code="content.javascript" />

		<!-- Extracted document text (PDF visible text) -->
		<CodeBlock v-if="content.text" title="Extracted text" :code="content.text" />

		<!-- LNK -->
		<div v-if="content.arguments || content.target" class="bg-secondary flex flex-col gap-1 rounded-lg p-3 text-sm">
			<div v-if="content.target"><span class="text-secondary">Target:</span> <code>{{ content.target }}</code></div>
			<div v-if="content.arguments"><span class="text-secondary">Arguments:</span> <code>{{ content.arguments }}</code></div>
			<div v-if="content.working_dir"><span class="text-secondary">Working dir:</span> <code>{{ content.working_dir }}</code></div>
		</div>

		<!-- PE capabilities -->
		<div v-if="content.capabilities?.length" class="flex flex-col gap-2">
			<span class="text-secondary text-xs font-medium">Capabilities (capa)</span>
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

const content = computed<InspectorContent>(() => props.result?.content ?? {})

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
