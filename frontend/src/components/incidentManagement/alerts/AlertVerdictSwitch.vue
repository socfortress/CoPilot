<template>
	<n-popselect
		v-model:value="verdictSelected"
		v-model:show="listVisible"
		:options="verdictOptions"
		:disabled="loading"
		size="medium"
		scrollable
		to="body"
	>
		<slot :loading />
	</n-popselect>

	<!--
		False positive is the only verdict that opens a dialog: a reason is mandatory for it,
		because a free-form classification is exactly what made the previous tag-based
		workaround useless for reporting. True positive and Clear submit straight away.
	-->
	<n-modal
		v-model:show="showReasonDialog"
		display-directive="show"
		preset="card"
		title="Mark as false positive"
		:style="{ maxWidth: 'min(560px, 90vw)' }"
		segmented
		@after-leave="onDialogClosed()"
	>
		<div class="flex flex-col gap-4">
			<n-form-item label="Reason" :show-feedback="false">
				<n-select
					v-model:value="reasonSelected"
					:options="reasonOptions"
					placeholder="Why is this a false positive?"
				/>
			</n-form-item>

			<n-form-item :label="noteLabel" :show-feedback="false">
				<n-input
					v-model:value="noteValue"
					type="textarea"
					:rows="3"
					:maxlength="1024"
					show-count
					placeholder="Optional detail for the next analyst who sees this alert"
				/>
			</n-form-item>
		</div>

		<template #footer>
			<div class="flex items-center justify-end gap-3">
				<n-button secondary :disabled="loading" @click="showReasonDialog = false">Cancel</n-button>
				<n-button type="primary" :loading :disabled="!reasonSelected" @click="submitFalsePositive()">
					Mark false positive
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Alert, AlertVerdict, FalsePositiveReason } from "@/types/incidentManagement/alerts"
import { NButton, NFormItem, NInput, NModal, NPopselect, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { falsePositiveReasonLabel } from "@/components/incidentManagement/alerts/utils"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	alert: Alert
}>()
const emit = defineEmits<{
	(e: "updated", value: Alert): void
}>()

const { alert } = toRefs(props)

// Sentinel for the "back to untriaged" option. Distinct from `null`, which is what the
// popselect holds before a choice is made — using null for both would make the watcher
// unable to tell "nothing picked yet" from "picked Clear".
const CLEAR_VERDICT = "__CLEAR__" as const
type VerdictChoice = AlertVerdict | typeof CLEAR_VERDICT

const loading = ref(false)
const message = useMessage()
const listVisible = ref(false)
const showReasonDialog = ref(false)
const reasonSelected = ref<FalsePositiveReason | null>(null)
const noteValue = ref<string>("")

const verdict = computed(() => alert.value.verdict)
const verdictSelected = ref<VerdictChoice | null>(null)

const verdictOptions = computed<{ label: string; value: VerdictChoice; disabled?: boolean }[]>(() => [
	{ label: "True positive", value: "TRUE_POSITIVE" },
	{ label: "False positive", value: "FALSE_POSITIVE" },
	// Only offered once there is something to clear.
	{ label: "Clear verdict", value: CLEAR_VERDICT, disabled: !verdict.value }
])

const reasonOptions: { label: string; value: FalsePositiveReason }[] = (
	[
		"EXPECTED_ACTIVITY",
		"KNOWN_APPLICATION",
		"AUTHORIZED_USER",
		"RULE_TOO_SENSITIVE",
		"OTHER"
	] as FalsePositiveReason[]
).map(value => ({ label: falsePositiveReasonLabel(value), value }))

const noteLabel = computed(() => (reasonSelected.value === "OTHER" ? "Note (recommended for Other)" : "Note"))

function applyVerdict(
	nextVerdict: AlertVerdict | null,
	reason: FalsePositiveReason | null,
	note: string | null
) {
	loading.value = true

	Api.incidentManagement.alerts
		.updateAlertVerdict(alert.value.id, nextVerdict, reason, note)
		.then(res => {
			if (res.data.success) {
				emit("updated", {
					...alert.value,
					verdict: nextVerdict,
					verdict_reason: nextVerdict === "FALSE_POSITIVE" ? reason : null,
					verdict_note: nextVerdict ? note : null,
					// The authoritative attribution comes back on the next fetch; this keeps the
					// row from showing a stale previous classifier in the meantime.
					verdict_by: nextVerdict ? alert.value.verdict_by : null,
					verdict_at: nextVerdict ? new Date() : null
				})
				showReasonDialog.value = false
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
				resetSelection()
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			resetSelection()
		})
		.finally(() => {
			loading.value = false
		})
}

function submitFalsePositive() {
	if (!reasonSelected.value) return
	applyVerdict("FALSE_POSITIVE", reasonSelected.value, noteValue.value.trim() || null)
}

function resetSelection() {
	verdictSelected.value = verdict.value ?? null
}

function onDialogClosed() {
	// Cancelling the dialog must not leave the popselect showing a verdict that was never
	// saved, otherwise re-picking "False positive" is a no-op against the watcher.
	if (alert.value.verdict !== "FALSE_POSITIVE") {
		resetSelection()
	}
	reasonSelected.value = null
	noteValue.value = ""
}

watch(verdictSelected, value => {
	if (value === null) return

	if (value === CLEAR_VERDICT) {
		if (verdict.value) applyVerdict(null, null, null)
		return
	}

	if (value === verdict.value) return

	if (value === "FALSE_POSITIVE") {
		reasonSelected.value = alert.value.verdict_reason ?? null
		noteValue.value = alert.value.verdict_note ?? ""
		showReasonDialog.value = true
		return
	}

	applyVerdict(value, null, null)
})

// Keep the control in step when the alert is replaced by a refetch or a sibling edit.
watch(verdict, () => resetSelection())

onBeforeMount(() => {
	resetSelection()
})
</script>
