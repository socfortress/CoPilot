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
									v-if="current[job.name].length"
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
										:class="toneClass(statusTone(worstStatus(current[job.name])))"
										:data-testid="`talon-ops-job-status-${job.name}`"
									>
										{{ worstStatus(current[job.name]) }}
									</span>
									<span
										v-if="states[job.name].running"
										class="text-secondary"
										title="This tick's runs are still coming in: a customer not run yet shows its previous run"
										:data-testid="`talon-ops-job-running-${job.name}`"
									>
										· running ({{ states[job.name].running?.done }} of
										{{ states[job.name].running?.total }})
									</span>
									<span class="text-secondary">
										· {{ formatTime(lastFinished(current[job.name])) }}
									</span>
									<span v-if="current[job.name].length > 1" class="text-tertiary">
										· {{ current[job.name].length }} customers
									</span>
									<Icon
										:name="openRuns.has(job.name) ? 'carbon:chevron-up' : 'carbon:chevron-down'"
										:size="12"
									/>
								</button>
								<span
									v-else-if="hiddenPlatformJob(job, isAdmin)"
									class="text-tertiary"
									:data-testid="`talon-ops-job-platform-${job.name}`"
								>
									Platform job (admins only)
								</span>
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
										v-for="run of current[job.name]"
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
// visible ("9 enabled · last runs ok", or what isn't: amber, red with a failed run). Expanded, a
// compact table: each job's title, its schedule in words (the cron in a tooltip), the worst status of
// its newest tick's runs, its next run, and "Run now" for an admin on an enabled job. `last_runs` also
// holds older runs (`jobState`): while the newest tick is still in progress the job is "running (k of
// n)", and each customer not run yet counts with its previous run. A click on the status lists the
// runs, worst first: customer, status, when, counts, Talon's fixed error text. A platform job's runs
// are an admin's: anyone else sees "admins only".
//
// Run now reads the job's runs, queues a run in Talon, then polls `GET /talon/ops/runs?job=` every few
// seconds for up to two minutes for this click's runs: `manual` ones of the tick in the workflow id
// Talon returns (`freshRuns`; never this browser's clock). Once every customer's run is in and
// `QUIET_POLLS` polls in a row find no more, or at the timeout with some in, it reloads the jobs and
// the findings once (`ran`) and says what they found ("N new, N updated, N resolved"); with none,
// "still running; refresh later". A refusal (403, 404, v2 off) stops the polling and is shown;
// anything transient is tried again. Unmounting stops it too.
import type { JobState, RunResult, Tone } from "./ops"
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type { TalonOpsJob, TalonOpsRun } from "@/types/talonOps"
import { NAlert, NButton, NTag, NTooltip } from "naive-ui"
import { computed, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { formatTime } from "../health/health"
import {
	byWorst,
	customerText,
	expectedRuns,
	freshRuns,
	hiddenPlatformJob,
	humanSchedule,
	isTransient,
	jobLabel,
	jobsSummary,
	jobState,
	lastFinished,
	QUIET_POLLS,
	RUN_POLL_MS,
	RUN_WATCH_MS,
	runCounts,
	runResult,
	RUNS_LIMIT,
	runsDone,
	statusTone,
	triggerTick,
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

/** Tries of the runs read before queueing, a second apart, while it fails transiently. */
const PRE_READ_TRIES = 3

const expanded = ref(false)
const openRuns = ref(new Set<string>())
const queueing = ref<string | null>(null)
const watching = ref(new Set<string>())
const messages = ref<Record<string, RunResult>>({})
/** One per job being queued or watched: aborting it stops that job's polling and requests. */
const watches = new Map<string, AbortController>()

const summary = computed(() => jobsSummary(jobs, isAdmin, Date.now()))
/** Each job's state (`jobState`), its runs worst first; read again with the jobs. */
const states = computed<Record<string, JobState>>(() => {
	const now = Date.now()
	return Object.fromEntries(
		jobs.map(job => {
			const state = jobState(job, now)
			return [job.name, { ...state, runs: byWorst(state.runs) }]
		})
	)
})
const current = computed<Record<string, TalonOpsRun[]>>(() =>
	Object.fromEntries(Object.entries(states.value).map(([name, state]) => [name, state.runs]))
)

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

type RunsRead = { runs: TalonOpsRun[] } | { failure: TalonOpsFailure }

/** The job's recent runs, or why they couldn't be read. */
async function readRuns(name: string, signal: AbortSignal): Promise<RunsRead> {
	try {
		const { data } = await Api.talonOps.listRuns({ job: name, limit: RUNS_LIMIT }, signal)
		return { runs: data.items }
	} catch (err) {
		return { failure: opsFailure(err) }
	}
}

/** The run ids Talon has before the click (the fallback when Talon returns no workflow id), or null. */
async function knownRuns(name: string, signal: AbortSignal): Promise<Set<string> | null> {
	for (let attempt = 1; attempt <= PRE_READ_TRIES; attempt++) {
		const read = await readRuns(name, signal)
		if ("runs" in read) return new Set(read.runs.map(run => run.id))
		if (signal.aborted || !isTransient(read.failure) || attempt === PRE_READ_TRIES) return null
		await sleep(1000, signal)
	}
	return null
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
	try {
		const before = await knownRuns(name, own.signal)
		if (own.signal.aborted) return
		const { data } = await Api.talonOps.runNow(name)
		if (own.signal.aborted) return
		const tick = triggerTick(data.workflow_id)
		queueing.value = null
		if (tick === null && before === null) {
			messages.value[name] = {
				type: "info",
				text: `${label} is queued to run now. Its runs can't be followed here: refresh later.`
			}
			watches.delete(name)
			return
		}
		messages.value[name] = {
			type: "info",
			text: `${label} is queued to run now. Its results show here when it finishes.`
		}
		await watch(job, label, tick, before, own)
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
	tick: number | null,
	before: Set<string> | null,
	own: AbortController
) {
	const name = job.name
	const expected = expectedRuns(job)
	const deadline = Date.now() + RUN_WATCH_MS
	let fresh: TalonOpsRun[] = []
	let quiet = 0
	watching.value.add(name)
	try {
		while (!own.signal.aborted) {
			await sleep(RUN_POLL_MS, own.signal)
			if (own.signal.aborted) return
			const read = await readRuns(name, own.signal)
			if (own.signal.aborted) return
			if ("failure" in read && !isTransient(read.failure)) {
				if (fresh.length) emit("ran")
				messages.value[name] = {
					type: "error",
					text: `${label}: its runs can't be read (${read.failure.detail}).`
				}
				return
			}
			const found = "runs" in read ? freshRuns(read.runs, tick, before) : fresh
			const grew = found.length > fresh.length
			if ("runs" in read) fresh = found
			const ready = fresh.length > 0 && runsDone(fresh, expected)
			quiet = ready && !grew ? quiet + 1 : 0
			const timedOut = Date.now() >= deadline
			// Every run expected is in, and polls in a row found no more (a customer added since the last tick).
			const done = ready && (quiet >= QUIET_POLLS || timedOut)
			if (done || timedOut) {
				if (fresh.length) emit("ran")
				messages.value[name] = runResult(label, fresh, expected, done, timedOut)
				return
			}
			if (grew && fresh.length < expected) {
				messages.value[name] = runResult(label, fresh, expected, false, false)
			}
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
