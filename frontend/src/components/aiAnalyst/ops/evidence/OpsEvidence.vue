<template>
	<DiskForecastEvidence
		v-if="kind === 'disk_forecast'"
		:evidence
		:is-admin
		:settings
		:schedule
		:last-seen="finding.last_seen ?? null"
	/>
	<AgentHygieneEvidence v-else-if="kind === 'agent_hygiene'" :evidence :kind="finding.kind" />
	<QuietEndpointsEvidence v-else-if="kind === 'quiet_endpoints'" :evidence />
	<MappingDriftEvidence v-else-if="kind === 'mapping_drift'" :evidence :kind="finding.kind" />
	<StorageUsageEvidence v-else-if="kind === 'storage_usage'" :evidence />
	<NoisyEventsEvidence v-else-if="kind === 'noisy_events'" :evidence />
	<ExclusionEvidence v-else-if="kind === 'exclusion_candidates'" :evidence />
	<FiguresEvidence v-else-if="kind === 'figures'" :evidence :job="finding.job" />
</template>

<script setup lang="ts">
// A finding's evidence view, chosen by its job (`viewKind`). The drawer renders this only when
// `viewKind` found one: evidence that doesn't parse gets the generic list instead.
import type { TalonOpsFinding } from "@/types/talonOps"
import { computed } from "vue"
import AgentHygieneEvidence from "./AgentHygieneEvidence.vue"
import DiskForecastEvidence from "./DiskForecastEvidence.vue"
import { viewKind } from "./evidence"
import ExclusionEvidence from "./ExclusionEvidence.vue"
import FiguresEvidence from "./FiguresEvidence.vue"
import MappingDriftEvidence from "./MappingDriftEvidence.vue"
import NoisyEventsEvidence from "./NoisyEventsEvidence.vue"
import QuietEndpointsEvidence from "./QuietEndpointsEvidence.vue"
import StorageUsageEvidence from "./StorageUsageEvidence.vue"

const {
	finding,
	isAdmin = false,
	settings = null,
	schedule = null
} = defineProps<{
	finding: Pick<TalonOpsFinding, "job" | "kind" | "evidence"> & Partial<Pick<TalonOpsFinding, "last_seen">>
	isAdmin?: boolean
	settings?: Record<string, unknown> | null
	/** The job's cron (`TalonOpsJob.schedule`). */
	schedule?: string | null
}>()

const evidence = computed(() => finding.evidence)
const kind = computed(() => viewKind(finding))
</script>
