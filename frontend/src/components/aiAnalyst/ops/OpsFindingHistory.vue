<template>
	<section aria-label="History" class="flex flex-col gap-2" data-testid="talon-ops-history">
		<h4 class="text-secondary text-xs font-semibold uppercase">History</h4>
		<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
			<dt class="text-secondary">First seen</dt>
			<dd data-testid="talon-ops-history-first-seen"><TimeText :iso="finding.first_seen" /></dd>
			<dt class="text-secondary">Last seen</dt>
			<dd data-testid="talon-ops-history-last-seen"><TimeText :iso="finding.last_seen" /></dd>
			<template v-if="finding.stale_since">
				<dt class="text-secondary">Not measured since</dt>
				<dd class="text-warning" data-testid="talon-ops-history-stale"><TimeText :iso="finding.stale_since" /></dd>
			</template>
			<template v-if="finding.resolved_at">
				<dt class="text-secondary">Resolved</dt>
				<dd data-testid="talon-ops-history-resolved">
					<TimeText :iso="finding.resolved_at" />
					<template v-if="finding.resolved_reason">
						({{ finding.resolved_reason.replace(/_/g, " ") }})
					</template>
				</dd>
			</template>
		</dl>

		<h5 class="text-secondary text-xs font-semibold">
			Runs of this job{{ finding.customer_code ? ` for ${finding.customer_code}` : "" }} since it was first seen
		</h5>
		<p v-if="!allowed" class="text-tertiary text-xs" data-testid="talon-ops-history-admins-only">
			A platform job's runs are for admins only.
		</p>
		<div v-else-if="loading" class="flex justify-center py-2" data-testid="talon-ops-history-loading">
			<n-spin size="small" />
		</div>
		<p v-else-if="failure" class="text-error text-xs" data-testid="talon-ops-history-error">
			The runs couldn't be read: <bdi>{{ failure }}</bdi>
		</p>
		<p v-else-if="!runs.length" class="text-tertiary text-xs" data-testid="talon-ops-history-empty">
			No runs since it was first seen are left in Talon's recent runs.
		</p>
		<template v-else>
			<ul class="flex flex-col gap-0.5 text-xs">
				<li v-for="run of runs" :key="run.id" class="text-secondary" data-testid="talon-ops-history-run">
					<span :class="toneClass(statusTone(run.status))">{{ run.status }}</span>
					·
					<TimeText :iso="run.finished_at ?? run.started_at ?? run.tick" :relative="false" />
					· {{ runCounts(run) }}
					<template v-if="run.error">
						·
						<bdi :class="toneClass(statusTone(run.status))">{{ run.error }}</bdi>
					</template>
				</li>
			</ul>
			<p class="text-tertiary text-xs">
				Up to the newest {{ HISTORY_RUNS }} runs. Talon doesn't record a finding's severity changes, so they aren't
				shown.
			</p>
		</template>
	</section>
</template>

<script setup lang="ts">
// A finding's history: when it was first and last seen, since when its job couldn't measure it, when
// it resolved, and its job's runs for its customer since it was first seen (status, time, counts,
// Talon's fixed error text). A platform finding's runs are an admin's: anyone else is told so and
// nothing is read. Talon keeps no severity trail, so none is shown or implied.
import type { Tone } from "./ops"
import type { TalonOpsFinding, TalonOpsRun } from "@/types/talonOps"
import { NSpin } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import TimeText from "./evidence/TimeText.vue"
import { canReadFindingRuns, findingRuns, HISTORY_RUNS, runCounts, statusTone } from "./ops"

const { finding, isAdmin = false } = defineProps<{
	finding: Pick<TalonOpsFinding, "id" | "job" | "customer_code" | "first_seen" | "last_seen" | "stale_since" | "resolved_at" | "resolved_reason">
	isAdmin?: boolean
}>()

const runs = ref<TalonOpsRun[]>([])
const loading = ref(false)
const failure = ref<string | null>(null)
let controller: AbortController | null = null

const allowed = computed(() => canReadFindingRuns(finding, isAdmin))

function toneClass(tone: Tone): string {
	if (tone === "error") return "text-error"
	if (tone === "warning") return "text-warning"
	return "text-secondary"
}

async function load() {
	controller?.abort()
	runs.value = []
	failure.value = null
	if (!allowed.value) return
	const own = new AbortController()
	controller = own
	loading.value = true
	try {
		const query =
			finding.customer_code === null
				? { job: finding.job, limit: HISTORY_RUNS }
				: { job: finding.job, customer_code: finding.customer_code, limit: HISTORY_RUNS }
		const { data } = await Api.talonOps.listRuns(query, own.signal)
		if (controller !== own) return
		runs.value = findingRuns(Array.isArray(data?.items) ? data.items : [], finding)
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		failure.value = opsFailure(err).detail
	} finally {
		if (controller === own) loading.value = false
	}
}

watch(() => [finding.id, finding.job, finding.customer_code, finding.first_seen, isAdmin], load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
