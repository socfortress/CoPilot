<template>
	<!--
		Shown between "the job exists" and "the result is readable".

		A spinner alone says only that something is happening; these steps say which
		one, and that the wait is expected. Detonation in particular runs minutes
		after the static tier is done — without naming the stage, a page sitting on
		partial content looks stalled.
	-->
	<div class="border-default flex flex-col overflow-hidden rounded-lg border">
		<div class="bg-secondary border-default flex items-center gap-3 border-b px-4 py-3">
			<n-spin :size="14" />
			<span class="text-default text-sm font-medium">{{ headline }}</span>
			<span class="text-tertiary ml-auto text-xs">this page updates on its own</span>
		</div>

		<div class="bg-border grid gap-px @2xl:grid-cols-3">
			<div v-for="step of steps" :key="step.key" class="bg-secondary flex items-start gap-3 p-4">
				<Icon
					:name="ICONS[step.state]"
					:size="16"
					class="mt-0.5 shrink-0"
					:class="[TONES[step.state], step.state === 'running' ? 'spin' : '']"
				/>
				<div class="flex min-w-0 flex-col gap-1">
					<span :class="SECTION_LABEL">{{ step.label }}</span>
					<span class="text-secondary text-xs">{{ step.detail }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisJob, FileAnalysisStatus } from "@/types/file-analysis"
import { NSpin } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"

type StepState = "done" | "running" | "pending" | "failed"

const props = defineProps<{ job: FileAnalysisJob | null; reputationPending?: boolean }>()

const ICONS: Record<StepState, string> = {
	done: "carbon:checkmark-outline",
	running: "carbon:circle-dash",
	pending: "carbon:radio-button",
	failed: "carbon:warning-alt"
}

const TONES: Record<StepState, string> = {
	done: "text-success",
	running: "text-primary",
	pending: "text-tertiary",
	failed: "text-error"
}

function stateOf(status?: FileAnalysisStatus): StepState {
	if (status === "done") return "done"
	if (status === "failed") return "failed"
	if (status === "running") return "running"
	return "pending"
}

const steps = computed(() => {
	const job = props.job
	const staticState = stateOf(job?.static_status)
	const list = [
		{
			key: "static",
			label: "Static inspection",
			state: staticState,
			detail:
				staticState === "done"
					? "Parsed — nothing was executed"
					: staticState === "failed"
						? "The inspector could not parse this file"
						: "Parsing structure, strings and behaviour"
		},
		{
			key: "reputation",
			label: "Reputation",
			state: (props.reputationPending ? "running" : staticState === "done" ? "done" : "pending") as StepState,
			detail: props.reputationPending ? "Waiting on the VirusTotal scan" : "Hash looked up against VirusTotal"
		}
	]

	if (job?.sandbox_enabled) {
		const dyn = stateOf(job.dynamic_status)
		list.push({
			key: "detonation",
			label: "Detonation",
			state: dyn,
			detail:
				dyn === "running"
					? "Running in the sandbox — this takes a few minutes"
					: dyn === "done"
						? "Sandbox report collected"
						: dyn === "failed"
							? "The sandbox run did not complete"
							: "Queued for the sandbox"
		})
	}

	return list
})

const headline = computed(() => {
	const running = steps.value.find(s => s.state === "running")
	return running ? `${running.label} in progress…` : "Analysis in progress…"
})
</script>

<style scoped lang="scss">
:deep(.spin) {
	animation: spin 1.4s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}
</style>
