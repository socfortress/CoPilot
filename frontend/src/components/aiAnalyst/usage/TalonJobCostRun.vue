<template>
	<div class="flex flex-col gap-5" data-testid="talon-cost-and-run">
		<section>
			<div class="text-secondary mb-2 text-sm font-semibold uppercase">Cost</div>
			<TalonJobCost :job-id />
		</section>
		<section v-if="runView" data-testid="talon-run-section">
			<div class="text-secondary mb-2 text-sm font-semibold uppercase">Run timeline</div>
			<TalonRunTimeline :job-id />
		</section>
	</div>
</template>

<script setup lang="ts">
// "Cost & run" for one investigation's job (decision D): its cost from the usage API, and its run
// timeline from Phoenix when availability's `run_view` says the connector is set up. Mounted only
// with "Talon v2" on.
import { useTalonV2Availability } from "@/composables/useTalonV2Availability"
import TalonJobCost from "./TalonJobCost.vue"
import TalonRunTimeline from "./TalonRunTimeline.vue"

const { jobId } = defineProps<{ jobId: string }>()

const { runView } = useTalonV2Availability()
</script>
