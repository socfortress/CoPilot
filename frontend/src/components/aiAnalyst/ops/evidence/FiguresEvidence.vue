<template>
	<div v-if="items.length" data-testid="talon-ops-evidence-key-figures">
		<EvidenceFigures :items />
	</div>
</template>

<script setup lang="ts">
// `cluster_health` and `silent_log_sources`: their key figures with units ("Show as a list" has the rest).
import type { Evidence } from "./evidence"
import { computed } from "vue"
import { figures, figureSpecs } from "./evidence"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence, job } = defineProps<{ evidence: Evidence | null; job: string }>()
const items = computed(() => figures(evidence, figureSpecs(job)))
</script>
