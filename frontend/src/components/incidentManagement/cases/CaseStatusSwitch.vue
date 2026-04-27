<template>
	<n-popselect
		v-model:value="statusSelected"
		v-model:show="listVisible"
		:options="statusOptions"
		:disabled="loading"
		size="medium"
		scrollable
		to="body"
	>
		<slot :loading />
	</n-popselect>

	<!-- Soft-warning modal (issue #792 Phase 3 backend / Phase 5 UI). Fires
		 when closing a case with mandatory tasks not marked DONE. Cancel
		 reverts the dropdown; "Close anyway" re-submits with force=true. -->
	<n-modal
		v-model:show="showWarning"
		preset="card"
		title="Mandatory tasks incomplete"
		style="max-width: 560px"
	>
		<p class="mb-3">
			This case has {{ pendingTasks.length }} mandatory task{{ pendingTasks.length === 1 ? "" : "s" }}
			that {{ pendingTasks.length === 1 ? "is" : "are" }} not marked
			<strong>Done</strong>. Closing anyway will record the override in the case timeline.
		</p>

		<ul class="text-sm">
			<li v-for="t in pendingTasks" :key="t.id" class="mb-1">
				<span class="font-medium">{{ t.title }}</span>
				<span class="text-tertiary"> — {{ humanStatus(t.status) }}</span>
			</li>
		</ul>

		<template #footer>
			<div class="flex justify-end gap-2">
				<n-button @click="cancelClose">Cancel</n-button>
				<n-button type="warning" :loading="loading" @click="confirmForceClose">
					Close anyway
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { Case, CaseStatus } from "@/types/incidentManagement/cases.d"
import type { CaseTask, CaseTaskStatus } from "@/types/incidentManagement/caseTemplates.d"
import { NButton, NModal, NPopselect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"

const props = defineProps<{
	caseData: Case
}>()
const emit = defineEmits<{
	(e: "updated", value: Case): void
}>()

const { caseData } = toRefs(props)

const loading = ref(false)
const message = useMessage()
const listVisible = ref(false)
const status = computed(() => caseData.value.case_status)
const statusOptions = ref<{ label: string; value: CaseStatus }[]>([
	{ label: "Open", value: "OPEN" },
	{ label: "In progress", value: "IN_PROGRESS" },
	{ label: "Closed", value: "CLOSED" }
])
const statusSelected = ref<CaseStatus | null>(null)

// Soft-warning state
const showWarning = ref(false)
const pendingTasks = ref<CaseTask[]>([])
// Snapshot the status the dropdown was switching to so we can resubmit with
// force=true after the user confirms. Separate from statusSelected because
// canceling needs to revert the dropdown without retriggering this watcher.
const pendingTargetStatus = ref<CaseStatus | null>(null)

function humanStatus(s: CaseTaskStatus): string {
	return s === "TODO" ? "to do" : s === "DONE" ? "done" : "not necessary"
}

async function callUpdate(target: CaseStatus, force = false) {
	loading.value = true
	try {
		const res = await Api.incidentManagement.cases.updateCaseStatus(
			caseData.value.id,
			target,
			force
		)
		const data: any = res.data

		// Soft-warning shape from backend: success=false, requires_confirmation=true,
		// incomplete_mandatory_tasks=[]. Treat as a confirmation flow rather than an error.
		if (data && data.requires_confirmation === true) {
			pendingTasks.value = data.incomplete_mandatory_tasks ?? []
			pendingTargetStatus.value = target
			showWarning.value = true
			return
		}

		if (data?.success) {
			emit("updated", { ...caseData.value, case_status: target })
		} else {
			message.warning(data?.message || "An error occurred. Please try again later.")
			// Revert dropdown on plain failure.
			revertDropdown()
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		revertDropdown()
	} finally {
		loading.value = false
	}
}

function revertDropdown() {
	if (status.value && statusSelected.value !== status.value) {
		statusSelected.value = status.value
	}
}

function cancelClose() {
	showWarning.value = false
	pendingTargetStatus.value = null
	pendingTasks.value = []
	revertDropdown()
}

async function confirmForceClose() {
	if (pendingTargetStatus.value == null) {
		showWarning.value = false
		return
	}
	const target = pendingTargetStatus.value
	showWarning.value = false
	await callUpdate(target, true)
	pendingTargetStatus.value = null
	pendingTasks.value = []
}

watch(statusSelected, newVal => {
	if (newVal && newVal !== status.value) {
		callUpdate(newVal, false)
	}
})

onBeforeMount(() => {
	if (status.value) {
		statusSelected.value = status.value
	}
})
</script>
