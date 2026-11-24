<template>
	<!-- The worst severities' failure counts, each a word and a number: compact enough for a table row. -->
	<span class="inline-flex flex-wrap items-center gap-1" data-testid="cloud-severity-tags">
		<n-tag v-if="!shown.length" type="success" size="tiny" round :bordered="false">No failures</n-tag>
		<n-tag
			v-for="item of shown"
			:key="item.severity"
			:type="SEVERITY_TAGS[item.severity]"
			size="tiny"
			round
			:bordered="false"
			:title="`${item.count} failing at ${SEVERITY_LABELS[item.severity]} severity`"
		>
			<span class="tabular-nums">{{ item.count }}</span>
			{{ SEVERITY_LABELS[item.severity].toLowerCase() }}
		</n-tag>
	</span>
</template>

<script setup lang="ts">
import type { CloudScanCounts, CloudSeverity } from "@/types/cloud-assessment"
import { NTag } from "naive-ui"
import { computed } from "vue"
import { failedBySeverity, SEVERITY_LABELS, SEVERITY_TAGS } from "./utils"

const { counts, severities = ["critical", "high", "medium", "low"] } = defineProps<{
	counts: CloudScanCounts
	severities?: CloudSeverity[]
}>()

const shown = computed(() => {
	const by = failedBySeverity(counts)
	return severities.filter(severity => by[severity] > 0).map(severity => ({ severity, count: by[severity] }))
})
</script>
