<template>
	<!-- Scanning in progress -->
	<n-alert v-if="!reputation && loading" type="default" :bordered="false" class="text-sm">
		<div class="flex items-center gap-2">
			<n-spin :size="14" />
			<span>VirusTotal — scanning… (a first-seen file is uploaded and scanned by 70+ engines; this can take a minute)</span>
		</div>
	</n-alert>

	<!-- Result present -->
	<n-alert v-else-if="reputation" :type="alertType" :bordered="false" class="text-sm">
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
			<Icon :name="VtIcon" :size="16" />
			<span class="font-semibold">VirusTotal</span>

			<template v-if="reputation.found">
				<span>
					<b>{{ reputation.malicious ?? 0 }}</b> / {{ reputation.total ?? "?" }} engines flagged this as malicious<span
						v-if="(reputation.suspicious ?? 0) > 0"
					>
						({{ reputation.suspicious }} suspicious)</span>.
				</span>
				<n-tag v-if="reputation.family" type="error" size="small" round :bordered="false">{{ reputation.family }}</n-tag>
			</template>
			<template v-else>
				<span>Not previously seen by VirusTotal.</span>
			</template>

			<n-tag v-if="reputation.submitted" size="small" round :bordered="false" type="warning">uploaded to VT</n-tag>

			<a v-if="reputation.permalink" :href="reputation.permalink" target="_blank" rel="noopener" class="underline">
				View on VirusTotal ↗
			</a>
		</div>
		<div v-if="reputation.note" class="text-secondary mt-1 text-xs">{{ reputation.note }}</div>
	</n-alert>
</template>

<script setup lang="ts">
import type { FileAnalysisReputation } from "@/types/file-analysis"
import { NAlert, NSpin, NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ reputation?: FileAnalysisReputation | null; loading?: boolean }>()

const VtIcon = "carbon:virus-outbreak"

const alertType = computed<"error" | "warning" | "success" | "default">(() => {
	const r = props.reputation
	if (!r || !r.found) return "default"
	const mal = r.malicious ?? 0
	if (mal >= 5) return "error"
	if (mal >= 1 || (r.suspicious ?? 0) >= 1) return "warning"
	return "success"
})
</script>
