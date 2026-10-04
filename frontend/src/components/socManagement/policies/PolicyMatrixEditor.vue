<template>
	<div class="policy-matrix flex flex-col gap-5" data-testid="policy-matrix">
		<section v-for="entity of ENTITIES" :key="entity" class="flex flex-col gap-2">
			<h4 :class="SECTION_LABEL" class="m-0">{{ entity === "alert" ? "Alerts" : "Cases" }}</h4>
			<n-scrollbar x-scrollable :data-testid="`policy-scroll-${entity}`">
				<n-table class="policy-table" size="small" :data-testid="`policy-table-${entity}`">
					<thead>
						<tr>
							<th>Severity</th>
							<th>Value</th>
							<th>Respond within</th>
							<th>Resolve within</th>
							<th>Counted in</th>
							<th />
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="cell of cellsOf(entity)"
							:key="cell.severity"
							:class="{ 'is-inherited': cell.inherit }"
							:data-testid="`policy-row-${entity}-${cell.severity}`"
						>
							<td><SeverityTag :severity="cell.severity" /></td>
							<td>
								<n-switch
									:value="!cell.inherit"
									size="small"
									:disabled="readonly"
									:data-testid="`policy-own-${entity}-${cell.severity}`"
									@update:value="own => setOwn(cell, own)"
								>
									<template #checked>{{ ownLabel }}</template>
									<template #unchecked>{{ inheritLabel(cell) }}</template>
								</n-switch>
							</td>
							<td>
								<TargetInput
									:model-value="shown(cell).ack_minutes"
									:disabled="readonly || cell.inherit"
									:placeholder="cell.inherit && !shown(cell).known ? 'on save' : 'none'"
									:aria-label="`${entity} ${cell.severity} respond within`"
									:test-id="`policy-ack-${entity}-${cell.severity}`"
									@update:model-value="value => update(cell, { ack_minutes: value })"
								/>
							</td>
							<td>
								<TargetInput
									:model-value="shown(cell).resolve_minutes"
									:disabled="readonly || cell.inherit"
									:placeholder="cell.inherit && !shown(cell).known ? 'on save' : 'none'"
									:aria-label="`${entity} ${cell.severity} resolve within`"
									:test-id="`policy-resolve-${entity}-${cell.severity}`"
									@update:model-value="value => update(cell, { resolve_minutes: value })"
								/>
							</td>
							<td>
								<n-switch
									:value="shown(cell).business_hours"
									size="small"
									:disabled="readonly || cell.inherit"
									:aria-label="`${entity} ${cell.severity} counts business hours`"
									:data-testid="`policy-hours-${entity}-${cell.severity}`"
									@update:value="hours => update(cell, { business_hours: hours })"
								>
									<template #checked>Business hours</template>
									<template #unchecked>24/7</template>
								</n-switch>
							</td>
							<td class="text-xs">
								<span
									v-if="cellError(cell)"
									class="inline-flex items-center gap-1"
									:style="{ color: TONE_COLOR.bad }"
								>
									<Icon name="carbon:warning-filled" :size="13" />
									{{ cellError(cell) }}
								</span>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-scrollbar>
		</section>
	</div>
</template>

<script setup lang="ts">
// The SLA matrix of one scope: entity × severity → (respond within, resolve within,
// counted 24/7 or in the customer's business hours).
// Each cell either has a value of its own in this scope or follows the next scope out
// (customer → global → built-in default). An inheriting cell shows the value it follows
// when that is known; one switched to inherit in this session shows it after saving.
import type { EditablePolicyCell } from "../utils"
import type { SlaEntity } from "@/types/soc-management"
import { NScrollbar, NSwitch, NTable } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import SeverityTag from "../ui/SeverityTag.vue"
import { cellError, ENTITIES, TONE_COLOR } from "../utils"
import TargetInput from "./TargetInput.vue"

const {
	original,
	scope,
	readonly = false
} = defineProps<{
	/** The cells as loaded, to show what an inheriting cell follows. */
	original: EditablePolicyCell[]
	scope: "global" | "customer"
	readonly?: boolean
}>()

const cells = defineModel<EditablePolicyCell[]>({ required: true })

// Computed, not a constant: the editor is reused when the scope changes.
const ownLabel = computed(() => (scope === "customer" ? "Override" : "Custom"))

function inheritLabel(cell: EditablePolicyCell) {
	return scope === "customer" && cell.inheritedFrom === "global" ? "Global" : "Default"
}

function cellsOf(entity: SlaEntity) {
	return cells.value.filter(cell => cell.entity === entity)
}

function originalOf(cell: EditablePolicyCell) {
	return original.find(item => item.entity === cell.entity && item.severity === cell.severity)
}

/** What the inputs show: own values, or — while inheriting — the inherited ones if known. */
function shown(cell: EditablePolicyCell) {
	const source = cell.inherit ? originalOf(cell) : cell
	if (source && (!cell.inherit || source.inherit)) {
		const { ack_minutes, resolve_minutes, business_hours } = source
		return { ack_minutes, resolve_minutes, business_hours, known: true }
	}
	return { ack_minutes: null, resolve_minutes: null, business_hours: false, known: false }
}

function replace(target: EditablePolicyCell, patch: Partial<EditablePolicyCell>) {
	cells.value = cells.value.map(cell =>
		cell.entity === target.entity && cell.severity === target.severity ? { ...cell, ...patch } : cell
	)
}

function setOwn(cell: EditablePolicyCell, own: boolean) {
	// Switching to a value of its own starts from what the cell showed, so the analyst
	// edits the inherited figure rather than retyping it.
	const start = shown(cell)
	replace(
		cell,
		own
			? {
					inherit: false,
					ack_minutes: start.ack_minutes,
					resolve_minutes: start.resolve_minutes,
					business_hours: start.business_hours
				}
			: { inherit: true }
	)
}

function update(
	cell: EditablePolicyCell,
	patch: Pick<Partial<EditablePolicyCell>, "ack_minutes" | "resolve_minutes" | "business_hours">
) {
	replace(cell, patch)
}
</script>

<style scoped>
.policy-table th,
.policy-table td {
	white-space: nowrap;
}

/* The page's section-label voice, over n-table's own header style. */
.policy-table th {
	font-size: 10px;
	font-weight: 500;
	letter-spacing: 0.05em;
	text-transform: uppercase;
	color: var(--fg-tertiary-color);
}

.is-inherited td:first-child {
	opacity: 0.75;
}
</style>
