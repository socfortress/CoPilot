<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-mapping-drift">
		<div v-if="view.kind === 'field_limit'" class="flex flex-col gap-1" data-testid="talon-ops-evidence-field-limit">
			<div class="flex flex-wrap items-baseline justify-between gap-2 text-sm">
				<span>
					{{ view.lowerBound ? "At least " : "" }}{{ view.used.toLocaleString() }} fields of a limit of
					{{ view.limit.toLocaleString() }}
				</span>
				<span class="font-mono tabular-nums">{{ pctText(Math.round((view.used / view.limit) * 1000) / 10) }}</span>
			</div>
			<n-progress
				type="line"
				:percentage="view.percent"
				:show-indicator="false"
				:height="8"
				:status="view.percent >= 95 ? 'error' : view.percent >= 80 ? 'warning' : 'default'"
				:aria-label="`${view.used} fields of a limit of ${view.limit}`"
			/>
			<p v-if="view.lowerBound" class="text-tertiary text-xs">
				A lower bound: the mapping listing was cut, so some object fields weren't counted.
			</p>
		</div>

		<div v-else-if="view.kind === 'field_growth'" class="text-sm" data-testid="talon-ops-evidence-field-growth">
			<span class="font-mono tabular-nums">{{ view.before.toLocaleString() }}</span>
			<span class="text-secondary"> → </span>
			<span class="font-mono font-semibold tabular-nums">{{ view.after.toLocaleString() }}</span>
			<span class="text-secondary"> fields across the family's indices</span>
		</div>

		<div v-else class="overflow-x-auto">
			<table class="w-full text-left text-xs" :data-testid="`talon-ops-evidence-${view.kind}`">
				<thead class="text-secondary">
					<tr v-if="view.kind === 'type_conflict'">
						<th class="py-1 pr-3 font-medium">Field</th>
						<th class="py-1 font-medium">Types</th>
					</tr>
					<tr v-else>
						<th class="py-1 pr-3 font-medium">Field</th>
						<th class="py-1 pr-3 font-medium">Problem</th>
						<th class="py-1 pr-3 font-medium">Mapped as</th>
						<th class="py-1 font-medium">Needs</th>
					</tr>
				</thead>
				<tbody v-if="view.kind === 'type_conflict'">
					<tr v-for="row of view.rows" :key="row.field" class="border-default border-t" data-testid="talon-ops-evidence-row">
						<td class="py-1 pr-3 font-mono break-all">
							<bdi>{{ row.field }}</bdi>
							<span v-if="row.talon" class="text-warning font-sans"> · Talon relies on it</span>
						</td>
						<td class="py-1 font-mono"><bdi>{{ row.types }}</bdi></td>
					</tr>
				</tbody>
				<tbody v-else>
					<tr v-for="row of view.rows" :key="row.field" class="border-default border-t" data-testid="talon-ops-evidence-row">
						<td class="py-1 pr-3 font-mono break-all"><bdi>{{ row.field }}</bdi></td>
						<td class="py-1 pr-3">{{ row.problem }}</td>
						<td class="py-1 pr-3 font-mono break-all"><bdi>{{ row.mapped }}</bdi></td>
						<td class="py-1 font-mono"><bdi>{{ row.needs }}</bdi></td>
					</tr>
				</tbody>
			</table>
			<p v-if="view.more" class="text-tertiary mt-1 text-xs" data-testid="talon-ops-evidence-more">
				+{{ view.more.toLocaleString() }} more
			</p>
		</div>

		<EvidenceFigures :items="view.figures" />
	</div>
</template>

<script setup lang="ts">
// `mapping_drift`, by kind: `field_limit` as a bar of fields used against the limit, `type_conflict` a
// table of field and types, `field_growth` the family's field count before → after, `talon_fields` a
// table of field and problem.
import type { Evidence } from "./evidence"
import { NProgress } from "naive-ui"
import { computed } from "vue"
import { mappingDriftView, pctText } from "./evidence"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence, kind } = defineProps<{ evidence: Evidence | null; kind: string }>()
const view = computed(() => mappingDriftView(evidence, kind))
</script>
