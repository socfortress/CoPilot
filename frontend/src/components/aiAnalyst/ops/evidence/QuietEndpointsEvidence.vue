<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-quiet-endpoints">
		<div v-if="view.conditions.length" class="flex flex-wrap gap-1" aria-label="Conditions" role="list">
			<n-tag
				v-for="condition of view.conditions"
				:key="condition.kind"
				size="small"
				:bordered="false"
				role="listitem"
				data-testid="talon-ops-evidence-condition"
			>
				{{ condition.label }}
			</n-tag>
		</div>
		<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
			<template v-for="seen of view.seen" :key="seen.label">
				<dt class="text-secondary">{{ seen.label }} last seen</dt>
				<dd :data-testid="`talon-ops-evidence-seen-${seen.label.toLowerCase()}`">
					<time v-if="seen.time" :title="seen.time.utc">
						{{ seen.time.relative }} · {{ seen.time.local }}
					</time>
					<span v-else class="text-tertiary">Never, or not known</span>
					<span v-if="seen.days !== null" class="text-tertiary"> · quiet for {{ daysText(seen.days) }}</span>
				</dd>
			</template>
		</dl>
		<EvidenceFigures :items="view.figures" />
	</div>
</template>

<script setup lang="ts">
// `quiet_endpoints`: the agent's conditions as tags, and when Wazuh and Velociraptor last saw it,
// relative and in local time (UTC in the tooltip).
import type { Evidence } from "./evidence"
import { NTag } from "naive-ui"
import { computed } from "vue"
import { daysText, quietEndpointsView } from "./evidence"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence } = defineProps<{ evidence: Evidence | null }>()
const view = computed(() => quietEndpointsView(evidence))
</script>
