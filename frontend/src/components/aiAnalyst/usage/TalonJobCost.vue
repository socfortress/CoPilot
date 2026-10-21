<template>
	<n-spin :show="loading" class="min-h-16" data-testid="talon-job-cost">
		<n-alert
			v-if="failure?.status === 404"
			type="default"
			:bordered="false"
			size="small"
			data-testid="talon-job-cost-not-found"
		>
			No Talon cost is recorded for this investigation (it may predate Talon v2, or not be visible to you).
		</n-alert>
		<n-alert
			v-else-if="failure?.status === 403"
			type="warning"
			:bordered="false"
			size="small"
			data-testid="talon-job-cost-forbidden"
		>
			Your role may not see Talon usage.
		</n-alert>
		<n-alert v-else-if="failure" type="error" :bordered="false" size="small" data-testid="talon-job-cost-error">
			{{ failure.detail }}
		</n-alert>

		<div v-else-if="usage" class="flex flex-col gap-4">
			<div class="flex flex-wrap items-center gap-3">
				<div class="flex items-baseline gap-2">
					<span class="text-secondary text-xs uppercase">Total</span>
					<span class="font-mono text-lg font-semibold" data-testid="talon-job-cost-total">
						{{ usage.total.cost_usd }}
					</span>
					<span class="text-secondary text-xs">USD</span>
				</div>
				<span class="text-secondary text-sm">
					{{ formatCount(usage.total.responses) }} responses · {{ formatCount(usage.total.input_tokens) }} in
					· {{ formatCount(usage.total.output_tokens) }} out
				</span>
				<n-tag
					v-if="!usage.total.cost_complete"
					type="warning"
					size="small"
					data-testid="talon-job-cost-incomplete"
				>
					Incomplete: {{ formatCount(usage.total.unpriced_responses) }} response(s) had no price
				</n-tag>
				<n-tag v-if="usage.truncated" type="info" size="small" data-testid="talon-job-cost-truncated">
					Truncated: not every run is listed; the total covers them all
				</n-tag>
				<n-tag v-if="usage.total.failed_attempts" size="small">
					{{ formatCount(usage.total.failed_attempts) }} failed attempt(s), billed and included
				</n-tag>
			</div>

			<div>
				<div class="text-secondary mb-1 text-xs font-semibold uppercase">Cost per run</div>
				<n-table v-if="usage.runs.length" size="small" :bordered="false" data-testid="talon-job-cost-runs">
					<thead>
						<tr>
							<th>Stage</th>
							<th>Model</th>
							<th>Started</th>
							<th class="text-right">Responses</th>
							<th class="text-right">Input</th>
							<th class="text-right">Output</th>
							<th class="text-right">Cost (USD)</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(run, index) of usage.runs" :key="index" data-testid="talon-job-cost-run">
							<td>
								<bdi>{{ run.stage ?? "—" }}</bdi>
							</td>
							<td>
								<bdi class="break-all">{{ run.model ?? "—" }}</bdi>
								<span v-if="run.provider" class="text-secondary ml-1 text-xs">
									<span>(</span>
									<bdi>{{ run.provider }}</bdi>
									<span>)</span>
								</span>
							</td>
							<td class="font-mono text-xs">
								{{ run.first_at ? formatDate(run.first_at, dFormats.datetime) : "—" }}
							</td>
							<td class="text-right font-mono">{{ formatCount(run.responses) }}</td>
							<td class="text-right font-mono">{{ formatCount(run.input_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(run.output_tokens) }}</td>
							<td class="text-right">
								<span class="font-mono" data-testid="talon-job-cost-run-cost">{{ run.cost_usd }}</span>
								<n-tag v-if="!run.cost_complete" type="warning" size="tiny" class="ml-2">
									incomplete
								</n-tag>
							</td>
						</tr>
					</tbody>
				</n-table>
				<p v-else class="text-secondary text-sm" data-testid="talon-job-cost-no-runs">
					No model runs recorded.
				</p>
			</div>

			<div v-if="stages.length">
				<div class="text-secondary mb-1 text-xs font-semibold uppercase">Stage durations</div>
				<div class="flex flex-wrap gap-2" data-testid="talon-job-cost-stages">
					<n-tag v-for="[stage, ms] of stages" :key="stage" size="small" data-testid="talon-job-cost-stage">
						{{ stage }}: {{ formatDurationMs(ms) }}
					</n-tag>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// One investigation's cost (decision D, per job): `GET /api/talon/v2/usage/investigations/{job_id}`,
// authorized by CoPilot from the job and its alert. The total and each run's cost are the API's
// decimal strings, shown as they came. 404: unknown or not visible (alike, on purpose); 403: a role
// the usage API doesn't serve.
import type { TalonFailure } from "@/api/endpoints/talonUsage"
import type { TalonInvestigationUsage } from "@/types/talonUsage"
import { NAlert, NSpin, NTable, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { talonFailure } from "@/api/endpoints/talonUsage"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { compareStages, formatCount, formatDurationMs } from "./usage"

const { jobId } = defineProps<{ jobId: string }>()

const dFormats = useSettingsStore().dateFormat
const usage = ref<TalonInvestigationUsage | null>(null)
const failure = ref<TalonFailure | null>(null)
const loading = ref(false)
let controller: AbortController | null = null

const stages = computed(() =>
	Object.entries(usage.value?.stage_durations_ms ?? {})
		.filter(([, ms]) => typeof ms === "number")
		.sort(([a], [b]) => compareStages(a, b))
)

async function load(id: string) {
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	usage.value = null
	try {
		const res = await Api.talonUsage.getInvestigationUsage(id, own.signal)
		if (controller === own) usage.value = res.data
	} catch (err) {
		if (controller === own && !own.signal.aborted) failure.value = talonFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

watch(
	() => jobId,
	id => load(id),
	{ immediate: true }
)
onBeforeUnmount(() => controller?.abort())
</script>
