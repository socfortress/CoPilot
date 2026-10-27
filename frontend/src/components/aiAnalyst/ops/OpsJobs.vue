<template>
	<section class="border-default rounded-lg border p-3" aria-label="Ops jobs" data-testid="talon-ops-jobs">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
				<h3 class="text-sm font-semibold">
					<button
						type="button"
						class="inline-flex items-center gap-1"
						:aria-expanded="expanded"
						aria-controls="talon-ops-jobs-table"
						data-testid="talon-ops-jobs-toggle"
						@click="expanded = !expanded"
					>
						<Icon :name="expanded ? 'carbon:chevron-down' : 'carbon:chevron-right'" :size="14" />
						Jobs
					</button>
				</h3>
				<span
					v-if="jobs.length"
					class="inline-flex items-center gap-1 text-xs"
					:class="toneClass(summary.tone)"
					:data-tone="summary.tone"
					data-testid="talon-ops-jobs-summary"
				>
					<Icon
						v-if="summary.tone !== 'ok'"
						:name="summary.tone === 'error' ? 'carbon:error-filled' : 'carbon:warning-alt-filled'"
						:size="12"
					/>
					<bdi>{{ summary.text }}</bdi>
				</span>
			</div>
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

		<div
			v-show="expanded"
			id="talon-ops-jobs-table"
			class="mt-2 overflow-x-auto"
			data-testid="talon-ops-jobs-table"
		>
			<p v-if="!jobs.length && !loading" class="text-tertiary text-sm" data-testid="talon-ops-jobs-empty">
				Talon reported no ops jobs.
			</p>
			<table v-else class="w-full text-left text-xs">
				<thead class="text-secondary">
					<tr>
						<th class="py-1 pr-3 font-medium">Job</th>
						<th class="py-1 pr-3 font-medium">Schedule</th>
						<th class="py-1 pr-3 font-medium">Last run</th>
						<th class="py-1 pr-3 font-medium">Next run</th>
						<th v-if="isAdmin" class="py-1"><span class="sr-only">Actions</span></th>
					</tr>
				</thead>
				<tbody>
					<template v-for="job of jobs" :key="job.name">
						<tr class="border-default border-t align-top" :data-testid="`talon-ops-job-${job.name}`">
							<td class="py-1.5 pr-3">
								<div class="flex flex-wrap items-center gap-1.5">
									<span class="text-sm font-medium">
										<bdi>{{ job.title || jobLabel(job.name) }}</bdi>
									</span>
									<n-tag
										:type="job.enabled ? 'success' : 'default'"
										size="tiny"
										:bordered="false"
										data-testid="talon-ops-job-enabled"
									>
										{{ job.enabled ? "Enabled" : "Off" }}
									</n-tag>
									<n-tag
										v-if="job.enabled && job.schedule_status && job.schedule_status !== 'ACTIVE'"
										type="warning"
										size="tiny"
										:bordered="false"
									>
										Schedule {{ job.schedule_status.toLowerCase() }}
									</n-tag>
								</div>
								<code class="text-tertiary">{{ job.name }}</code>
							</td>
							<td class="py-1.5 pr-3 whitespace-nowrap">
								<n-tooltip :disabled="!job.schedule">
									<template #trigger>
										<span :data-testid="`talon-ops-job-schedule-${job.name}`">
											{{ humanSchedule(job.schedule) }}
										</span>
									</template>
									<span :data-testid="`talon-ops-job-cron-${job.name}`">
										Cron (UTC):
										<code>{{ job.schedule }}</code>
									</span>
								</n-tooltip>
							</td>
							<td class="py-1.5 pr-3" data-testid="talon-ops-job-last-run">
								<button
									v-if="jobRuns(job).length"
									type="button"
									class="inline-flex flex-wrap items-center gap-1 text-left hover:underline"
									:aria-expanded="openRuns.has(job.name)"
									:aria-controls="`talon-ops-job-runs-${job.name}`"
									:title="
										openRuns.has(job.name) ? 'Hide the runs' : 'Show the newest run per customer'
									"
									:data-testid="`talon-ops-job-runs-toggle-${job.name}`"
									@click="toggleRuns(job.name)"
								>
									<span
										:class="toneClass(statusTone(worstStatus(jobRuns(job))))"
										:data-testid="`talon-ops-job-status-${job.name}`"
									>
										{{ worstStatus(jobRuns(job)) }}
									</span>
									<span class="text-secondary">· {{ formatTime(jobRuns(job)[0].finished_at) }}</span>
									<span v-if="jobRuns(job).length > 1" class="text-tertiary">
										· {{ jobRuns(job).length }} customers
									</span>
									<Icon
										:name="openRuns.has(job.name) ? 'carbon:chevron-up' : 'carbon:chevron-down'"
										:size="12"
									/>
								</button>
								<span v-else class="text-tertiary">No run yet</span>
							</td>
							<td class="py-1.5 pr-3 whitespace-nowrap" data-testid="talon-ops-job-next-run">
								{{ job.next_run ? formatTime(job.next_run) : "—" }}
							</td>
							<td v-if="isAdmin" class="py-1 text-right">
								<n-button
									size="tiny"
									secondary
									:disabled="!job.enabled || queueing !== null || watching.has(job.name)"
									:loading="queueing === job.name || watching.has(job.name)"
									:title="runTitle(job)"
									:data-testid="`talon-ops-run-${job.name}`"
									@click="runNow(job)"
								>
									<template #icon><Icon name="carbon:play" :size="12" /></template>
									Run now
								</n-button>
							</td>
						</tr>
						<tr
							v-if="openRuns.has(job.name)"
							:id="`talon-ops-job-runs-${job.name}`"
							:data-testid="`talon-ops-job-runs-${job.name}`"
						>
							<td :colspan="isAdmin ? 5 : 4" class="pb-2 pl-3">
								<ul class="flex flex-col gap-0.5">
									<li
										v-for="run of jobRuns(job)"
										:key="run.id"
										class="text-secondary"
										data-testid="talon-ops-job-run"
									>
										<bdi class="font-medium">{{ customerText(run.customer_code) }}</bdi>
										·
										<span :class="toneClass(statusTone(run.status))">{{ run.status }}</span>
										· {{ formatTime(run.finished_at) }} · {{ runCounts(run) }}
										<template v-if="run.error">
											·
											<bdi :class="toneClass(statusTone(run.status))">{{ run.error }}</bdi>
										</template>
									</li>
								</ul>
							</td>
						</tr>
					</template>
				</tbody>
			</table>
		</div>

		<n-alert
			v-for="[name, message] of Object.entries(messages)"
			:key="name"
			class="mt-2"
			:type="message.type"
			:bordered="false"
			closable
			:data-job="name"
			data-testid="talon-ops-run-message"
			@close="dismiss(name)"
		>
			<bdi>{{ message.text }}</bdi>
		</n-alert>
	</section>
</template>

<script setup lang="ts">
// The ops jobs (`GET /talon/ops/jobs`), collapsed by default under a one-line summary that stays
// visible ("9 enabled · last runs ok", or the jobs whose last runs weren't ok, amber, red with a failed
// one). Expanded, a compact table: each job's title, its schedule in words (the cron in a tooltip), the
// worst status of its newest run per customer (`last_runs`; a click lists them: customer, status, when,
// counts, Talon's fixed error text), its next run, and "Run now" for an admin on an enabled job.
//
// Run now queues a run in Talon, then polls the job's runs (`GET /talon/ops/runs?job=`) every few
// seconds for up to two minutes. When runs Talon didn't have at the click have finished, the page
// reloads the jobs and the findings (`ran`) and says what they found ("N new, N updated, N resolved");
// with none by then, "still running; refresh later". Unmounting stops the polling.
import type { RunResult, Tone } from "./ops"
import type { TalonOpsJob, TalonOpsRun } from "@/types/talonOps"
import { NAlert, NButton, NTag, NTooltip } from "naive-ui"
import { computed, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { formatTime } from "../health/health"
import {
	customerText,
	expectedRuns,
	freshRuns,
	humanSchedule,
	jobLabel,
	jobRuns,
	jobsSummary,
	RUN_POLL_MS,
	RUN_WATCH_MS,
	runCounts,
	runResult,
	RUNS_LIMIT,
	runsDone,
	statusTone,
	worstStatus
} from "./ops"

const {
	jobs,
	loading = false,
	isAdmin = false
} = defineProps<{ jobs: TalonOpsJob[]; loading?: boolean; isAdmin?: boolean }>()
const emit = defineEmits<{
	(e: "refresh"): void
	/** Run now's runs finished: reload the jobs and the findings. */
	(e: "ran"): void
}>()

const expanded = ref(false)
const openRuns = ref(new Set<string>())
const queueing = ref<string | null>(null)
const watching = ref(new Set<string>())
const messages = ref<Record<string, RunResult>>({})
/** One per job being queued or watched: aborting it stops that job's polling and requests. */
const watches = new Map<string, AbortController>()

const summary = computed(() => jobsSummary(jobs))

function toneClass(tone: Tone): string {
	if (tone === "error") return "text-error"
	if (tone === "warning") return "text-warning"
	return "text-secondary"
}

function toggleRuns(name: string) {
	if (openRuns.value.has(name)) openRuns.value.delete(name)
	else openRuns.value.add(name)
}

function runTitle(job: TalonOpsJob): string {
	if (!job.enabled) return "Enable the job in Talon (TALON_OPS_JOBS) to run it"
	if (watching.value.has(job.name)) return "Waiting for this job's run to finish"
	return "Run this job now"
}

function stop(name: string) {
	watches.get(name)?.abort()
	watches.delete(name)
	watching.value.delete(name)
}

function dismiss(name: string) {
	stop(name)
	delete messages.value[name]
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
	return new Promise(resolve => {
		const timer = setTimeout(resolve, ms)
		signal.addEventListener(
			"abort",
			() => {
				clearTimeout(timer)
				resolve()
			},
			{ once: true }
		)
	})
}

/** The job's recent runs, or null when they couldn't be read (the next poll tries again). */
async function readRuns(name: string, signal: AbortSignal): Promise<TalonOpsRun[] | null> {
	try {
		const { data } = await Api.talonOps.listRuns({ job: name, limit: RUNS_LIMIT }, signal)
		return data.items
	} catch {
		return null
	}
}

async function runNow(job: TalonOpsJob) {
	const name = job.name
	if (queueing.value || watching.value.has(name)) return
	stop(name)
	const own = new AbortController()
	watches.set(name, own)
	queueing.value = name
	delete messages.value[name]
	const label = jobLabel(name)
	const clickedAt = Date.now()
	try {
		// The runs Talon has now: any other finished run from here on is this one's.
		const known = await readRuns(name, own.signal)
		if (own.signal.aborted) return
		await Api.talonOps.runNow(name)
		if (own.signal.aborted) return
		messages.value[name] = {
			type: "info",
			text: `${label} is queued to run now. Its results show here when it finishes.`
		}
		queueing.value = null
		await watch(job, label, known ? new Set(known.map(run => run.id)) : null, clickedAt, own)
	} catch (err) {
		if (!own.signal.aborted) messages.value[name] = { type: "error", text: opsFailure(err).detail }
		if (watches.get(name) === own) watches.delete(name)
	} finally {
		if (queueing.value === name) queueing.value = null
	}
}

async function watch(
	job: TalonOpsJob,
	label: string,
	before: Set<string> | null,
	clickedAt: number,
	own: AbortController
) {
	const name = job.name
	const expected = expectedRuns(job)
	const deadline = Date.now() + RUN_WATCH_MS
	let fresh: TalonOpsRun[] = []
	watching.value.add(name)
	try {
		while (!own.signal.aborted) {
			await sleep(RUN_POLL_MS, own.signal)
			if (own.signal.aborted) return
			const runs = await readRuns(name, own.signal)
			if (own.signal.aborted) return
			const found = runs ? freshRuns(runs, before, clickedAt) : fresh
			const grew = found.length > fresh.length
			if (grew) fresh = found
			const done = fresh.length > 0 && runsDone(fresh, expected)
			const timedOut = !done && Date.now() >= deadline
			if (grew) emit("ran")
			if (grew || done || timedOut) messages.value[name] = runResult(label, fresh, expected, done, timedOut)
			if (done || timedOut) return
		}
	} finally {
		if (watches.get(name) === own) {
			watches.delete(name)
			watching.value.delete(name)
		}
	}
}

onBeforeUnmount(() => {
	for (const own of watches.values()) own.abort()
	watches.clear()
})
</script>
