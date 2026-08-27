<template>
	<!-- The primary list: the signatures that actually drove the verdict. -->
	<div v-if="variant === 'primary'" class="flex flex-col gap-2">
		<span :class="SECTION_LABEL">{{ label }} ({{ signatures.length }})</span>
		<div class="flex flex-col gap-2">
			<div
				v-for="(sig, i) of signatures"
				:key="i"
				class="bg-secondary flex flex-wrap items-start gap-3 rounded-lg p-3"
			>
				<Icon :name="SigIcon" :size="16" :class="severityClass(sig.severity)" class="mt-0.5 shrink-0" />
				<div class="flex min-w-0 grow flex-col">
					<span class="text-sm font-medium break-all">{{ sig.name }}</span>
					<span v-if="sig.description" class="text-secondary text-xs">{{ sig.description }}</span>
				</div>
				<n-tag v-if="sig.severity" size="tiny" round :bordered="false" :type="severityTag(sig.severity)">
					sev {{ sig.severity }}
				</n-tag>
				<div class="flex flex-wrap gap-1">
					<n-tag v-for="m of sig.mitre || []" :key="m" size="tiny" round :bordered="false">{{ m }}</n-tag>
				</div>
			</div>
		</div>
	</div>

	<!-- The discounted lists: shown for context, dimmed, and folded away by default
	     so they cannot be mistaken for signal. Same card chrome as the rest of the
	     module — these used to be bare n-collapse blocks, the only two in the tab. -->
	<CollapsibleCard v-else default-collapsed>
		<template #header>
			<span :class="SECTION_LABEL">
				{{ label }}
				<span class="text-tertiary normal-case">({{ signatures.length }}) — {{ note }}</span>
			</span>
		</template>
		<div class="divide-border flex flex-col divide-y opacity-70">
			<div v-for="(sig, i) of signatures" :key="i" class="flex items-start gap-2 px-3 py-2 text-xs">
				<n-tag size="tiny" round :bordered="false" class="shrink-0">sev {{ sig.severity ?? "—" }}</n-tag>
				<div class="flex min-w-0 flex-col">
					<span class="font-medium break-all">{{ sig.name }}</span>
					<span v-if="sig.description" class="text-secondary">{{ sig.description }}</span>
				</div>
			</div>
		</div>
	</CollapsibleCard>
</template>

<script setup lang="ts">
/**
 * A CAPE signature list, in one of two registers.
 *
 * The tab renders three of these — the meaningful ones, the low-confidence
 * static-PE/.NET-JIT heuristics, and the environmental monitor baseline — and the
 * last two were near-identical copies of each other.
 */
import type { SandboxSignature } from "@/types/file-analysis"
import { NTag } from "naive-ui"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"

withDefaults(
	defineProps<{
		signatures: SandboxSignature[]
		label: string
		/** primary = drove the verdict; secondary = shown for context only. */
		variant?: "primary" | "secondary"
		/** Why a secondary list is discounted, said in the header. */
		note?: string
	}>(),
	{ variant: "primary", note: "not counted toward the verdict" }
)

const SigIcon = "carbon:rule"

// CAPE severities run 1–3 for ordinary behaviour; 4 and up is where a signature
// starts to convict on its own, which is why the scale tops out here.
function severityClass(severity?: number): string {
	if (!severity) return "text-secondary"
	if (severity >= 3) return "text-error"
	if (severity >= 2) return "text-warning"
	return "text-secondary"
}

function severityTag(severity?: number): "error" | "warning" | "default" {
	if (!severity) return "default"
	if (severity >= 3) return "error"
	if (severity >= 2) return "warning"
	return "default"
}
</script>
