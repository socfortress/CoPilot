<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-storage-usage">
		<EvidenceFigures :items="view.figures" />
		<EvidenceBars :groups="view.groups" />
		<p v-if="view.more" class="text-tertiary text-xs" data-testid="talon-ops-evidence-more">
			+{{ view.more.toLocaleString() }} more index patterns
		</p>
	</div>
</template>

<script setup lang="ts">
// `storage_usage`: the customer's totals, then per index pattern the GB stored and GB per day as bars.
import type { Evidence } from "./evidence"
import { computed } from "vue"
import { storageUsageView } from "./evidence"
import EvidenceBars from "./EvidenceBars.vue"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence } = defineProps<{ evidence: Evidence | null }>()
const view = computed(() => storageUsageView(evidence))
</script>
