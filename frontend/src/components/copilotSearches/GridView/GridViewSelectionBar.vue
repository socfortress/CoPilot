<template>
	<Transition name="selection-bar">
		<div
			v-if="selectMode && selectedRules.length > 0"
			class="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-5"
		>
			<div
				class="border-primary/35 bg-default ring-primary/20 pointer-events-auto flex w-full max-w-180 flex-wrap items-center gap-x-4 gap-y-3 rounded-xl border px-4 py-3 shadow-xl ring-3"
				role="toolbar"
				aria-label="Selection actions"
			>
				<div class="flex min-w-0 flex-col gap-0.5">
					<p class="text-default text-sm leading-tight">
						<span class="text-primary font-mono font-semibold tabular-nums">
							{{ selectedRules.length }}
						</span>
						{{ selectedRules.length === 1 ? " rule" : " rules" }}
					</p>
					<p class="text-tertiary text-xs leading-tight">
						<span class="font-mono tabular-nums">{{ provisionableCount }}</span>
						with Graylog query
					</p>
				</div>

				<div class="flex w-full flex-wrap items-center gap-2 sm:ml-auto sm:w-auto">
					<n-tooltip placement="top" class="max-w-120! px-2! py-1.5! text-xs!">
						<template #trigger>
							<n-button
								size="small"
								type="primary"
								:disabled="provisionableCount === 0"
								@click="showBulkProvisionModal = true"
							>
								<template #icon>
									<Icon :name="ProvisionIcon" />
								</template>
								Provision
							</n-button>
						</template>
						<template v-if="provisionableCount === 0">
							None of the selected rules has a Graylog query.
						</template>
						<template v-else>
							Provision {{ provisionableCount }} rule{{ provisionableCount === 1 ? "" : "s" }} as Graylog
							event definitions.
						</template>
					</n-tooltip>

					<n-button size="small" secondary @click="exportSelectedCsv">
						<template #icon>
							<Icon :name="ExportIcon" />
						</template>
						CSV
					</n-button>
					<n-button size="small" secondary @click="exportSelectedJson">
						<template #icon>
							<Icon :name="ExportIcon" />
						</template>
						JSON
					</n-button>

					<n-button size="small" quaternary @click="emit('clear')">Clear</n-button>
				</div>
			</div>
		</div>
	</Transition>

	<n-modal
		v-model:show="showBulkProvisionModal"
		preset="card"
		:style="{ maxWidth: 'min(560px, 92vw)' }"
		title="Bulk Provision Graylog Alerts"
		:bordered="false"
		segmented
	>
		<BulkProvisionForm
			v-if="showBulkProvisionModal"
			:rule-ids="ruleIdsWithGraylog"
			:provisionable-count
			@close="showBulkProvisionModal = false"
			@success="onBulkProvisionSuccess"
		/>
	</n-modal>
</template>

<script setup lang="ts">
import type { BulkProvisionGraylogAlertResponse, RuleSummary } from "@/types/copilotSearches.d"
import { saveAs } from "file-saver"
import { NButton, NModal, NTooltip } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import BulkProvisionForm from "../BulkProvisionForm.vue"

const props = defineProps<{
	selectMode: boolean
	selectedRules: RuleSummary[]
}>()

const emit = defineEmits<{
	(e: "clear"): void
	(e: "provision-success", result: BulkProvisionGraylogAlertResponse): void
}>()

const showBulkProvisionModal = ref(false)

const ProvisionIcon = "carbon:add-alt"
const ExportIcon = "carbon:download"

const provisionableCount = computed(() => props.selectedRules.filter(r => r.has_graylog_query).length)

const ruleIdsWithGraylog = computed(() => props.selectedRules.filter(r => r.has_graylog_query).map(r => r.id))

function onBulkProvisionSuccess(result: BulkProvisionGraylogAlertResponse) {
	emit("provision-success", result)
}

function exportSelectedCsv() {
	if (!props.selectedRules.length) return
	const header = [
		"id",
		"name",
		"severity",
		"platform",
		"status",
		"has_graylog_query",
		"mitre_attack_id",
		"description"
	]
	const rows = props.selectedRules.map(r => [
		r.id,
		r.name,
		r.severity,
		r.platform,
		r.status,
		String(r.has_graylog_query),
		(r.mitre_attack_id || []).join("|"),
		(r.description || "").replace(/\s+/g, " ")
	])
	const csv = [header, ...rows]
		.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))
		.join("\n")
	const stamp = new Date().toISOString().slice(0, 10)
	saveAs(new Blob([csv], { type: "text/csv;charset=utf-8;" }), `copilot-searches-selected-${stamp}.csv`)
}

function exportSelectedJson() {
	if (!props.selectedRules.length) return
	const json = JSON.stringify(props.selectedRules, null, 2)
	const stamp = new Date().toISOString().slice(0, 10)
	saveAs(new Blob([json], { type: "application/json;charset=utf-8;" }), `copilot-searches-selected-${stamp}.json`)
}
</script>

<style scoped lang="scss">
.selection-bar-enter-active,
.selection-bar-leave-active {
	transition:
		opacity 0.22s ease,
		transform 0.22s ease;
}
.selection-bar-enter-from,
.selection-bar-leave-to {
	opacity: 0;
	transform: translateY(16px);
}
</style>
