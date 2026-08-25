<template>
	<!-- Compact panel, not a full-width alert band: VirusTotal is the second
	     opinion next to the static verdict, not a page-level announcement. -->
	<div class="flex flex-col gap-2">
		<template v-if="pending || (!reputation && loading)">
			<div class="text-secondary flex items-center gap-2 text-sm">
				<n-spin :size="13" />
				<span>checking reputation…</span>
			</div>
		</template>

		<template v-else-if="reputation?.skipped">
			<span class="text-tertiary text-sm">Not run for this analysis.</span>
		</template>

		<template v-else-if="reputation?.found">
			<div class="flex flex-wrap items-baseline gap-x-2">
				<span class="text-lg leading-none font-semibold" :class="ratioClass">
					{{ reputation.malicious ?? 0 }}/{{ reputation.total ?? "?" }}
				</span>
				<span class="text-tertiary text-xs">engines flagged it</span>
			</div>
			<div v-if="(reputation.suspicious ?? 0) > 0" class="text-tertiary text-xs">
				{{ reputation.suspicious }} more marked it suspicious
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<n-tag v-if="reputation.family" type="error" size="small" round :bordered="false">
					{{ reputation.family }}
				</n-tag>
				<n-tag v-if="reputation.submitted" size="small" round :bordered="false" type="warning">
					uploaded to VT
				</n-tag>
			</div>
		</template>

		<template v-else>
			<span class="text-secondary text-sm">Not previously seen.</span>
		</template>

		<a
			v-if="reputation?.permalink"
			:href="reputation.permalink"
			target="_blank"
			rel="noopener"
			class="text-primary text-xs hover:underline"
		>
			View on VirusTotal ↗
		</a>
		<span v-if="reputation?.note" class="text-tertiary text-xs">{{ reputation.note }}</span>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisReputation } from "@/types/file-analysis"
import { NSpin, NTag } from "naive-ui"
import { computed } from "vue"

const props = defineProps<{
	reputation?: FileAnalysisReputation | null
	loading?: boolean
	pending?: boolean
}>()

// Colour the ratio, not the whole panel — a red block for a 1/75 hit overstates it.
const ratioClass = computed(() => {
	const r = props.reputation
	if (!r?.found) return "text-secondary"
	const mal = r.malicious ?? 0
	if (mal >= 5) return "text-error"
	if (mal >= 1 || (r.suspicious ?? 0) >= 1) return "text-warning"
	return "text-success"
})
</script>
