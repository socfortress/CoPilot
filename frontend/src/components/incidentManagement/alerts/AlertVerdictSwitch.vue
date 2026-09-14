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
		Both verdicts open the same dialog (#1131). For a false positive the reason is
		mandatory, because a free-form classification is exactly what made the previous
		tag-based workaround useless for reporting; for a true positive the note is optional,
		so the dialog costs one extra click at most. Clear submits straight away.
	-->
	<n-modal
		v-model:show="showReasonDialog"
		display-directive="show"
		preset="card"
		:title="dialogTitle"
		:style="{ maxWidth: 'min(560px, 90vw)' }"
		segmented
		@after-leave="onDialogClosed()"
	>
		<div class="flex flex-col gap-4">
			<n-form-item v-if="pendingVerdict === 'FALSE_POSITIVE'" label="Reason" :show-feedback="false">
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
					:placeholder="notePlaceholder"
				/>
			</n-form-item>

			<!--
				The verdict note lives on the alert row (verdict_note) and is shown on the
				Overview card only; posting it as a comment as well puts it in the timeline
				the next analyst actually reads. Disabled when there is nothing to post.
			-->
			<n-checkbox v-model:checked="postAsComment" :disabled="!commentText">
				Also post as a comment on the alert
			</n-checkbox>
		</div>

		<template #footer>
			<div class="flex items-center justify-end gap-3">
				<n-button secondary :disabled="loading" @click="showReasonDialog = false">Cancel</n-button>
				<n-button type="primary" :loading :disabled="!canSubmit" @click="submitVerdict()">
					{{ submitLabel }}
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Alert, AlertComment, AlertVerdict, FalsePositiveReason } from "@/types/incidentManagement/alerts"
import { NButton, NCheckbox, NFormItem, NInput, NModal, NPopselect, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { falsePositiveReasonLabel, verdictLabel } from "@/components/incidentManagement/alerts/utils"
import { useAuthStore } from "@/stores/auth"
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

// The "also post as comment" choice is a per-analyst habit, not a per-alert one, so it
// is remembered across alerts and sessions. Browser-local only.
const POST_AS_COMMENT_STORAGE_KEY = "alertVerdict.postAsComment"

const loading = ref(false)
const message = useMessage()
const authStore = useAuthStore()
const listVisible = ref(false)
const showReasonDialog = ref(false)
const pendingVerdict = ref<AlertVerdict | null>(null)
const reasonSelected = ref<FalsePositiveReason | null>(null)
const noteValue = ref<string>("")
const postAsComment = ref<boolean>(readPostAsCommentPreference())

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

const trimmedNote = computed(() => noteValue.value.trim())

const dialogTitle = computed(() => `Mark as ${verdictLabel(pendingVerdict.value).toLowerCase()}`)
const submitLabel = computed(() => `Mark ${verdictLabel(pendingVerdict.value).toLowerCase()}`)

const noteLabel = computed(() => {
	if (pendingVerdict.value === "FALSE_POSITIVE") {
		return reasonSelected.value === "OTHER" ? "Note (recommended for Other)" : "Note"
	}
	return "Note (optional)"
})

const notePlaceholder = computed(() =>
	pendingVerdict.value === "TRUE_POSITIVE"
		? "What confirmed it? Optional, for the next analyst who sees this alert"
		: "Optional detail for the next analyst who sees this alert"
)

// A false positive needs its reason; a true positive can be confirmed without a word.
const canSubmit = computed(() => pendingVerdict.value === "TRUE_POSITIVE" || !!reasonSelected.value)

/**
 * Text posted to the alert's comments when the checkbox is on. The verdict line is
 * always there so the comment stays meaningful once the verdict is later changed or
 * cleared; the reason is included because for a false positive it *is* the finding.
 * Empty when there is nothing worth posting (a true positive with no note).
 */
const commentText = computed<string>(() => {
	if (!pendingVerdict.value) return ""

	if (pendingVerdict.value === "FALSE_POSITIVE") {
		if (!reasonSelected.value) return ""
		const header = `Marked as false positive — ${falsePositiveReasonLabel(reasonSelected.value)}`
		return trimmedNote.value ? `${header}\n\n${trimmedNote.value}` : header
	}

	return trimmedNote.value ? `Marked as true positive\n\n${trimmedNote.value}` : ""
})

function readPostAsCommentPreference(): boolean {
	try {
		return localStorage.getItem(POST_AS_COMMENT_STORAGE_KEY) === "true"
	} catch {
		return false
	}
}

function savePostAsCommentPreference(value: boolean) {
	try {
		localStorage.setItem(POST_AS_COMMENT_STORAGE_KEY, String(value))
	} catch {
		// Preference only — nothing to recover from.
	}
}

async function postComment(text: string): Promise<AlertComment | null> {
	try {
		const res = await Api.incidentManagement.alerts.newAlertComment({
			alert_id: alert.value.id,
			comment: text,
			created_at: new Date(),
			user_name: authStore.userName
		})
		if (res.data.success) {
			return res.data.comment
		}
		message.warning(res.data?.message || "Verdict saved, but the comment could not be posted.")
	} catch (err) {
		message.warning(getApiErrorMessage(err as ApiError) || "Verdict saved, but the comment could not be posted.")
	}
	return null
}

async function applyVerdict(
	nextVerdict: AlertVerdict | null,
	reason: FalsePositiveReason | null,
	note: string | null,
	comment: string | null = null
) {
	loading.value = true

	try {
		const res = await Api.incidentManagement.alerts.updateAlertVerdict(alert.value.id, nextVerdict, reason, note)

		if (!res.data.success) {
			message.warning(res.data?.message || "An error occurred. Please try again later.")
			resetSelection()
			return
		}

		const updated: Alert = {
			...alert.value,
			verdict: nextVerdict,
			verdict_reason: nextVerdict === "FALSE_POSITIVE" ? reason : null,
			verdict_note: nextVerdict ? note : null,
			// The authoritative attribution comes back on the next fetch; this keeps the
			// row from showing a stale previous classifier in the meantime.
			verdict_by: nextVerdict ? alert.value.verdict_by : null,
			verdict_at: nextVerdict ? new Date() : null
		}

		// The verdict is already saved at this point: a failed comment must not roll the
		// UI back to the old verdict, so it only warns and the emit below still happens.
		if (comment) {
			const posted = await postComment(comment)
			if (posted) {
				updated.comments = [...(alert.value.comments || []), posted]
			}
		}

		emit("updated", updated)
		showReasonDialog.value = false
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		resetSelection()
	} finally {
		loading.value = false
	}
}

function submitVerdict() {
	const next = pendingVerdict.value
	if (!next || !canSubmit.value) return

	const reason = next === "FALSE_POSITIVE" ? reasonSelected.value : null
	const comment = postAsComment.value && commentText.value ? commentText.value : null

	applyVerdict(next, reason, trimmedNote.value || null, comment)
}

function resetSelection() {
	verdictSelected.value = verdict.value ?? null
}

function openDialog(next: AlertVerdict) {
	pendingVerdict.value = next
	reasonSelected.value = null
	noteValue.value = ""
	// Re-read on every open: one switch is mounted per row, so a preference changed in
	// another row's dialog would otherwise stay invisible here until a reload.
	postAsComment.value = readPostAsCommentPreference()
	showReasonDialog.value = true
}

function onDialogClosed() {
	// Cancelling the dialog must not leave the popselect showing a verdict that was never
	// saved, otherwise re-picking the same option is a no-op against the watcher.
	if (alert.value.verdict !== pendingVerdict.value) {
		resetSelection()
	}
	pendingVerdict.value = null
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

	openDialog(value)
})

watch(postAsComment, value => savePostAsCommentPreference(value))

// Keep the control in step when the alert is replaced by a refetch or a sibling edit.
watch(verdict, () => resetSelection())

onBeforeMount(() => {
	resetSelection()
})
</script>
