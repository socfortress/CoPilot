<template>
	<div v-if="available" class="flex">
		<Badge v-if="loading" type="muted" size="small">
			<template #label>OpenCTI</template>
			<template #value><span class="text-secondary">checking…</span></template>
		</Badge>

		<Badge v-else-if="error" type="muted" size="small" point-cursor title="Retry" @click.stop="retry()">
			<template #label>OpenCTI</template>
			<template #value><span class="text-secondary">lookup failed · retry</span></template>
		</Badge>

		<Badge
			v-else-if="result?.found"
			type="splitted"
			size="small"
			bright
			point-cursor
			:color="scoreColor(summary.score)"
			:title="`Open the OpenCTI result for ${value}`"
			@click.stop="showModal = true"
		>
			<template #label>OpenCTI</template>
			<template #value>
				<span class="flex flex-wrap items-center gap-x-1.5">
					<span>Known</span>
					<span v-if="summary.score !== null">· score {{ summary.score }}</span>
					<span v-if="summary.reports">
						· {{ summary.reports }} {{ summary.reports === 1 ? "report" : "reports" }}
					</span>
					<span v-if="summary.labels.length">· {{ summary.labels.join(", ") }}</span>
					<span v-if="summary.moreLabels" class="text-secondary">+{{ summary.moreLabels }}</span>
				</span>
			</template>
		</Badge>

		<Badge v-else-if="result" type="muted" size="small">
			<template #label>OpenCTI</template>
			<template #value><span class="text-secondary">not found</span></template>
		</Badge>

		<n-modal
			v-model:show="showModal"
			preset="card"
			:style="{ maxWidth: 'min(640px, 90vw)' }"
			:bordered="false"
			segmented
			title="OpenCTI Enrichment"
		>
			<OpenCTILookupResult v-if="result" :lookup="result" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NModal } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { useOpenCTIIocLookup } from "@/composables/useOpenCTIIocLookup"
import OpenCTILookupResult from "./OpenCTILookupResult.vue"
import { scoreColor } from "./utils"

const { value } = defineProps<{
	value: string
}>()

const MAX_LABELS = 2

const { available } = useOpenCTIAvailability()
const { loading, error, result, retry } = useOpenCTIIocLookup(() => value, available)
const showModal = ref(false)

// One value can match several observables (Domain-Name and Hostname for the
// same string), so the badge summarises across all of them.
const summary = computed(() => {
	const observables = result.value?.observables || []
	const scores = observables.map(o => o.score).filter((s): s is number => s !== null)
	const labels = [...new Set(observables.flatMap(o => o.labels.map(l => l.value)))]
	return {
		score: scores.length ? Math.max(...scores) : null,
		reports: Math.max(0, ...observables.map(o => o.reports_count)),
		labels: labels.slice(0, MAX_LABELS),
		moreLabels: Math.max(0, labels.length - MAX_LABELS)
	}
})
</script>
