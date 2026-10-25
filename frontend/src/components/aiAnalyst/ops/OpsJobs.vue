<template>
	<section class="border-default rounded-lg border p-3" aria-label="Ops jobs" data-testid="talon-ops-jobs">
		<div class="mb-2 flex items-center justify-between gap-2">
			<h3 class="text-sm font-semibold">Jobs</h3>
			<n-button
				size="tiny"
				secondary
				:loading
				:disabled="loading"
				data-testid="talon-ops-jobs-refresh"
				@click="emit('refresh')"
			>
				<template #icon><Icon name="carbon:renew" :size="12" /></template>
				Refresh
			</n-button>
		</div>
		<p v-if="!jobs.length && !loading" class="text-tertiary text-sm" data-testid="talon-ops-jobs-empty">
			Talon reported no ops jobs.
		</p>
		<ul class="flex flex-col gap-2">
			<li
				v-for="job of jobs"
				:key="job.name"
				class="bg-secondary flex flex-wrap items-start justify-between gap-3 rounded-md px-3 py-2"
				:data-testid="`talon-ops-job-${job.name}`"
			>
				<div class="flex min-w-0 flex-col gap-1">
					<div class="flex flex-wrap items-center gap-2">
						<span class="font-medium">
							<bdi>{{ job.title || jobLabel(job.name) }}</bdi>
						</span>
						<code class="text-tertiary text-xs">{{ job.name }}</code>
						<n-tag
							:type="job.enabled ? 'success' : 'default'"
							size="small"
							:bordered="false"
							data-testid="talon-ops-job-enabled"
						>
							<template #icon>
								<Icon
									:name="job.enabled ? 'carbon:checkmark-filled' : 'carbon:pause-outline'"
									:size="12"
								/>
							</template>
							{{ job.enabled ? "Enabled" : "Off" }}
						</n-tag>
						<n-tag
							v-if="job.enabled && job.schedule_status && job.schedule_status !== 'ACTIVE'"
							type="warning"
							size="small"
							:bordered="false"
						>
							Schedule {{ job.schedule_status.toLowerCase() }}
						</n-tag>
					</div>
					<dl class="text-secondary grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-xs">
						<dt>Schedule</dt>
						<dd>
							<code>{{ job.schedule ?? "—" }}</code>
							UTC
						</dd>
						<dt>Last run</dt>
						<dd data-testid="talon-ops-job-last-run">
							<template v-if="job.last_run">
								<span :class="runClass(job.last_run.status)">{{ job.last_run.status }}</span>
								· {{ formatTime(job.last_run.finished_at) }}
								<template v-if="job.last_run.customer_code">
									·
									<bdi>{{ job.last_run.customer_code }}</bdi>
								</template>
								· {{ counts(job.last_run) }}
								<template v-if="job.last_run.error">
									·
									<bdi class="text-error">{{ job.last_run.error }}</bdi>
								</template>
							</template>
							<template v-else>No run yet</template>
						</dd>
						<dt>Next run</dt>
						<dd data-testid="talon-ops-job-next-run">
							{{ job.next_run ? formatTime(job.next_run) : "—" }}
						</dd>
					</dl>
				</div>
				<n-button
					v-if="isAdmin"
					size="small"
					secondary
					:disabled="!job.enabled || running !== null"
					:loading="running === job.name"
					:title="job.enabled ? 'Run this job now' : 'Enable the job in Talon (TALON_OPS_JOBS) to run it'"
					:data-testid="`talon-ops-run-${job.name}`"
					@click="runNow(job.name)"
				>
					<template #icon><Icon name="carbon:play" :size="14" /></template>
					Run now
				</n-button>
			</li>
		</ul>
		<n-alert
			v-if="runMessage"
			class="mt-2"
			:type="runMessage.type"
			:bordered="false"
			closable
			data-testid="talon-ops-run-message"
			@close="runMessage = null"
		>
			<bdi>{{ runMessage.text }}</bdi>
		</n-alert>
	</section>
</template>

<script setup lang="ts">
// The ops jobs (`GET /talon/ops/jobs`): each job's schedule, last run of the caller's customers
// (status, counts, when, its fixed error text) and next run, and "Run now" for an admin on an enabled
// job. Run now queues a run in Talon; the findings appear when it finishes.
import type { TalonOpsJob, TalonOpsRun } from "@/types/talonOps"
import { NAlert, NButton, NTag } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { formatTime } from "../health/health"
import { jobLabel } from "./ops"

const {
	jobs,
	loading = false,
	isAdmin = false
} = defineProps<{ jobs: TalonOpsJob[]; loading?: boolean; isAdmin?: boolean }>()
const emit = defineEmits<{ (e: "refresh"): void }>()

const running = ref<string | null>(null)
const runMessage = ref<{ type: "success" | "error"; text: string } | null>(null)

function counts(run: TalonOpsRun): string {
	const n = (value: number | null) => (typeof value === "number" ? value : "?")
	return `${n(run.new)} new, ${n(run.updated)} updated, ${n(run.resolved)} resolved`
}

function runClass(status: string): string {
	if (status === "failed") return "text-error"
	if (status === "partial" || status === "skipped") return "text-warning"
	return ""
}

async function runNow(name: string) {
	if (running.value) return
	running.value = name
	runMessage.value = null
	try {
		await Api.talonOps.runNow(name)
		runMessage.value = {
			type: "success",
			text: `${jobLabel(name)} is queued to run now. Its findings appear when it finishes.`
		}
	} catch (err) {
		runMessage.value = { type: "error", text: opsFailure(err).detail }
	} finally {
		running.value = null
	}
}
</script>
