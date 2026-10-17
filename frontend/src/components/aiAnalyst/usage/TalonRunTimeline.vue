<template>
	<n-spin :show="loading" class="min-h-16" data-testid="talon-run-timeline">
		<n-alert
			v-if="failure?.status === 409"
			type="default"
			:bordered="false"
			size="small"
			data-testid="talon-run-no-project"
		>
			No run view for this customer: its runs are not traced to a Phoenix project of its own, so CoPilot doesn't
			read them.
		</n-alert>
		<n-alert
			v-else-if="failure?.status === 404"
			type="default"
			:bordered="false"
			size="small"
			data-testid="talon-run-not-found"
		>
			No run view for this investigation.
		</n-alert>
		<n-alert v-else-if="failure" type="error" :bordered="false" size="small" data-testid="talon-run-error">
			{{ failure.detail }}
		</n-alert>

		<div v-else-if="timeline" class="flex flex-col gap-3">
			<div v-if="timeline.truncated || timeline.dropped" class="flex flex-wrap gap-2">
				<n-tag v-if="timeline.truncated" type="info" size="small" data-testid="talon-run-truncated">
					Truncated: the run has more spans than are shown
				</n-tag>
				<n-tag v-if="timeline.dropped" type="warning" size="small" data-testid="talon-run-dropped">
					{{ timeline.dropped }} span(s) left out: not this investigation's, unreadable or repeated
				</n-tag>
			</div>

			<p v-if="!layout.lanes.length" class="text-secondary py-4 text-sm" data-testid="talon-run-empty">
				No trace data for this run.
			</p>

			<div
				v-for="lane of layout.lanes"
				:key="lane.traceId"
				class="flex flex-col gap-1"
				data-testid="talon-run-lane"
			>
				<div class="text-secondary text-xs font-semibold uppercase" data-testid="talon-run-lane-label">
					{{ lane.label }}
				</div>
				<div
					v-for="row of lane.rows"
					:key="row.span.span_id"
					class="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] items-center gap-3 text-sm"
					data-testid="talon-run-span"
					:data-span-id="row.span.span_id"
					:data-depth="row.depth"
				>
					<div
						class="flex min-w-0 flex-wrap items-center gap-1.5"
						:style="{ paddingLeft: `${row.depth * 14}px` }"
					>
						<span class="truncate font-mono text-xs" data-testid="talon-run-span-name">
							{{ row.span.name }}
						</span>
						<n-tag size="tiny" :bordered="false">{{ row.span.kind }}</n-tag>
						<span
							v-if="spanSubject(row.span)"
							class="text-secondary truncate text-xs"
							data-testid="talon-run-span-subject"
						>
							{{ spanSubject(row.span) }}
						</span>
						<span
							v-if="tokensOf(row.span)"
							class="text-secondary text-xs"
							data-testid="talon-run-span-tokens"
						>
							{{ tokensOf(row.span) }}
						</span>
						<n-tag
							v-if="row.span.status_code === 'ERROR'"
							type="error"
							size="tiny"
							data-testid="talon-run-span-error"
						>
							ERROR
						</n-tag>
					</div>
					<div class="bg-secondary relative h-3 rounded-sm" :title="formatDurationMs(row.span.duration_ms)">
						<div
							class="absolute top-0 h-3 rounded-sm"
							:class="row.span.status_code === 'ERROR' ? 'bg-error' : 'bg-primary'"
							:style="{ left: `${row.leftPct}%`, width: `${row.widthPct}%` }"
							data-testid="talon-run-span-bar"
						/>
					</div>
				</div>
			</div>

			<p class="text-secondary text-xs" data-testid="talon-run-cost-note">
				Span names, kinds, times, tokens and status only; never prompts or outputs. Cost comes from Talon's
				usage ledger (above), not from these traces.
			</p>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// An investigation's run view (talon-analyst §5.4; CoPilot M5-9a): `GET /api/talon/v2/runs/{job_id}/timeline`,
// only when availability's `run_view` is on. A lane per trace, spans nested by `parent_id`, each bar
// placed by its start and sized by its duration (./run-timeline.ts). Only the DTO's named fields are
// rendered, and only as text: nothing from Phoenix is markup.
import type { TalonFailure } from "@/api/endpoints/talonUsage"
import type { TalonRunTimeline, TalonTimelineSpan } from "@/types/talonUsage"
import { NAlert, NSpin, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { talonFailure } from "@/api/endpoints/talonUsage"
import { layoutTimeline, spanSubject, spanTokens } from "./run-timeline"
import { formatCount, formatDurationMs } from "./usage"

const { jobId } = defineProps<{ jobId: string }>()

const timeline = ref<TalonRunTimeline | null>(null)
const failure = ref<TalonFailure | null>(null)
const loading = ref(false)
let controller: AbortController | null = null

const layout = computed(() => layoutTimeline(timeline.value?.spans ?? []))

function tokensOf(span: TalonTimelineSpan) {
	return spanTokens(span, formatCount)
}

async function load(id: string) {
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	timeline.value = null
	try {
		const res = await Api.talonUsage.getRunTimeline(id, own.signal)
		if (controller === own) timeline.value = res.data
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
