<template>
	<Transition name="fade-up">
		<div v-if="selectMode && selectedRules.length > 0" class="selection-footer flex flex-wrap justify-between">
			<div class="text-default text-sm">
				<strong>{{ selectedRules.length }}</strong>
				selected
				<span class="text-tertiary ml-2 text-xs">({{ provisionableCount }} with Graylog query)</span>
			</div>

			<div class="ml-auto flex flex-wrap items-center gap-2">
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
							Provision selected
						</n-button>
					</template>
					<template v-if="provisionableCount === 0">None of the selected rules has a Graylog query.</template>
					<template v-else>
						Provision {{ provisionableCount }} rule{{ provisionableCount === 1 ? "" : "s" }} as Graylog
						event definitions.
					</template>
				</n-tooltip>

				<n-button size="small" @click="exportSelectedCsv">
					<template #icon>
						<Icon :name="ExportIcon" />
					</template>
					CSV
				</n-button>
				<n-button size="small" @click="exportSelectedJson">
					<template #icon>
						<Icon :name="ExportIcon" />
					</template>
					JSON
				</n-button>

				<n-button size="small" quaternary @click="emit('clear')">Clear</n-button>
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
.selection-footer {
	position: fixed;
	bottom: 16px;
	left: 50%;
	transform: translateX(-50%);
	z-index: 50;
	display: flex;
	align-items: center;
	gap: 16px;
	min-width: min(680px, 92vw);
	max-width: 92vw;
	padding: 10px 16px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5);
}

.fade-up-enter-active,
.fade-up-leave-active {
	transition:
		opacity 0.2s ease,
		transform 0.2s ease;
}
.fade-up-enter-from,
.fade-up-leave-to {
	opacity: 0;
	transform: translate(-50%, 12px);
}
</style>
