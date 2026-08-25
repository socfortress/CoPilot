<template>
	<!-- Compact panel, not a full-width alert band: VirusTotal is the second
	     opinion next to the static verdict, not a page-level announcement.
	     Fixed rows rather than free-flowing lines, so the panel keeps the same
	     shape whether the file is unknown, clean or flagged by 29 engines. -->
	<div class="flex flex-col gap-3">
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
			<div class="flex items-baseline gap-2">
				<span class="text-2xl leading-none font-semibold" :class="ratioClass">
					{{ reputation.malicious ?? 0 }}
				</span>
				<span class="text-tertiary text-sm">/ {{ reputation.total ?? "?" }} engines flagged it</span>
			</div>

			<!-- Extra facts as label/value rows: they line up instead of running on. -->
			<div class="flex flex-col gap-1 text-xs">
				<div v-if="(reputation.suspicious ?? 0) > 0" class="flex items-baseline gap-2">
					<span class="text-tertiary w-20 shrink-0">suspicious</span>
					<span class="text-secondary">{{ reputation.suspicious }}</span>
				</div>
				<div v-if="reputation.family" class="flex items-baseline gap-2">
					<span class="text-tertiary w-20 shrink-0">family</span>
					<span class="text-error min-w-0 font-mono break-all">{{ reputation.family }}</span>
				</div>
				<div v-if="reputation.submitted" class="flex items-baseline gap-2">
					<span class="text-tertiary w-20 shrink-0">submitted</span>
					<span class="text-warning">uploaded to VT by this analysis</span>
				</div>
			</div>
		</template>

		<template v-else>
			<span class="text-secondary text-sm">Not previously seen.</span>
		</template>

		<span v-if="reputation?.note" class="text-tertiary text-xs">{{ reputation.note }}</span>

		<a
			v-if="reputation?.permalink"
			:href="reputation.permalink"
			target="_blank"
			rel="noopener"
			class="text-primary border-default mt-1 border-t pt-2 text-xs hover:underline"
		>
			View on VirusTotal ↗
		</a>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisReputation } from "@/types/file-analysis"
import { NSpin } from "naive-ui"
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
