<template>
	<n-button secondary :loading="merging" :size @click="openDialog()">
		<template #icon>
			<Icon :name="MergeIcon" />
		</template>
		Merge into Case
	</n-button>

	<n-modal
		v-model:show="showMergeBox"
		display-directive="show"
		preset="card"
		:title="`Merge ${alerts.length > 1 ? `${alerts.length} alerts` : 'alert'} into a case`"
		:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(540px, 90vh)', maxHeight: '80vh' }"
		content-class="flex flex-col overflow-hidden px-2! py-0!"
		segmented
		:closable="!busy"
		:mask-closable="!busy"
		:close-on-esc="!busy"
	>
		<!--
			Two ways in (#1131): pick a case that already exists, or create one right here and
			have the selected alerts attached to it in the same step — so the analyst never
			has to leave the alerts view, create the case, come back and reselect.

			"Create case & merge" is two requests (create, then link). The modal cannot be
			dismissed while either is in flight: closing it between the two would leave a
			case with nothing attached and no feedback about it.
		-->
		<n-tabs v-model:value="mode" type="segment" animated class="px-3 pt-3">
			<n-tab name="existing" :disabled="busy">Existing case</n-tab>
			<n-tab name="new" :disabled="busy">New case</n-tab>
		</n-tabs>

		<n-spin
			v-if="mode === 'existing'"
			:show="loadingCases"
			class="flex grow flex-col overflow-hidden"
			content-class="flex grow flex-col overflow-hidden"
		>
			<n-scrollbar class="flex grow flex-col" content-class="grow" trigger="none">
				<div class="flex flex-col gap-2 px-5 py-5">
					<template v-if="linkableCases.length">
						<CaseItem
							v-for="item of linkableCases"
							:key="item.id"
							:case-data="item"
							compact
							embedded
							:highlight="selectedCase?.id === item.id"
							@click="toggleSelectedCase(item)"
						/>
					</template>
					<template v-else>
						<n-empty v-if="!loadingCases" description="No items found" class="h-48 justify-center" />
					</template>
				</div>
			</n-scrollbar>
		</n-spin>

		<n-spin
			v-else
			:show="merging"
			class="flex grow flex-col overflow-hidden"
			content-class="flex grow flex-col overflow-hidden"
		>
			<n-scrollbar class="flex grow flex-col" content-class="grow" trigger="none">
				<div class="px-5 py-5">
					<CaseCreationForm
						v-model:submitting="creating"
						:prefill="newCasePrefill"
						submit-label="Create case & merge"
						@submitted="mergeIntoNewCase"
					/>
				</div>
			</n-scrollbar>
		</n-spin>

		<template v-if="mode === 'existing'" #footer>
			<div class="flex justify-end">
				<n-button type="success" :disabled="!selectedCase" :loading="merging" @click="linkCase()">
					<template #icon>
						<Icon :name="MergeIcon" />
					</template>
					Confirm Merge {{ selectedCase ? `with Case #${selectedCase.id}` : "" }}
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { Ref } from "vue"
import type { ApiError } from "@/types/common"
import type { Alert } from "@/types/incidentManagement/alerts"
import type { Case, CasePayload } from "@/types/incidentManagement/cases"
import _orderBy from "lodash/orderBy"
import _uniq from "lodash/uniq"
import { NButton, NEmpty, NModal, NScrollbar, NSpin, NTab, NTabs, useDialog, useMessage } from "naive-ui"
import { computed, h, inject, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import CaseCreationForm from "../cases/CaseCreationForm.vue"
import CaseItem from "../cases/CaseItem.vue"

const { alerts, size } = defineProps<{ alerts: Alert[]; size?: ButtonSize }>()

const emit = defineEmits<{
	(e: "updated", value: Alert): void
	(e: "merged"): void
}>()

const MergeIcon = "carbon:ibm-cloud-direct-link-1-connect"
const message = useMessage()
const dialog = useDialog()
const { routeIncidentManagementCases } = useNavigation()
const merging = ref(false)
const creating = ref(false)
const busy = computed(() => creating.value || merging.value)
const showMergeBox = ref(false)
const loadingCases = ref(false)
const linkableCases = inject<Ref<Case[]>>("linkable-cases", ref([]))
const selectedCase = ref<Case | null>(null)
const mode = ref<"existing" | "new">("existing")

/**
 * Seed for the "New case" form, mirroring what the backend's own case-from-alert
 * path copies from a single alert. Fields the selected alerts disagree on (customer,
 * assignee) are left blank rather than guessed from the first one: a wrong customer
 * on a case is a tenancy mistake, not a typo.
 */
const newCasePrefill = computed<Partial<CasePayload>>(() => {
	const single = (values: (string | null)[]) => {
		const distinct = _uniq(values)
		return distinct.length === 1 ? distinct[0] : null
	}

	const [first] = alerts
	const prefill: Partial<CasePayload> = {
		case_status: "OPEN",
		customer_code: single(alerts.map(o => o.customer_code)),
		assigned_to: single(alerts.map(o => o.assigned_to))
	}

	if (alerts.length === 1 && first) {
		prefill.case_name = first.alert_name
		prefill.case_description = first.alert_description
	} else if (first) {
		prefill.case_name = first.alert_name
		prefill.case_description = alerts.map(o => `- #${o.id} ${o.alert_name}`).join("\n")
	}

	return prefill
})

watch(showMergeBox, val => {
	if (val) {
		mode.value = "existing"
		if (!linkableCases.value.length) {
			getCasesList()
		}
	}
})

function updateAlert(updatedAlert: Alert) {
	emit("updated", updatedAlert)
}

function openDialog() {
	showMergeBox.value = true
}

function closeDialog() {
	showMergeBox.value = false
}

function toggleSelectedCase(caseEntity: Case) {
	if (selectedCase.value?.id === caseEntity.id) {
		selectedCase.value = null
	} else {
		selectedCase.value = caseEntity
	}
}

function getCasesList() {
	loadingCases.value = true

	Api.incidentManagement.cases
		.getCasesList({ page: 1, pageSize: 9999 })
		.then(res => {
			if (res.data.success) {
				linkableCases.value = _orderBy(res.data?.cases || [], ["id"], ["desc"])
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCases.value = false
		})
}

/**
 * The case is already created at this point (the form did it), so the only thing left
 * is the same link call the "Existing case" path makes. The case goes straight into the
 * existing-cases list so that, if the link fails, it can be retried from there instead
 * of creating a duplicate; the list is then re-read from the server once the merge is
 * done so it reflects what actually exists rather than what this component assumed.
 */
function mergeIntoNewCase(createdCase: Case) {
	linkableCases.value = [createdCase, ...linkableCases.value.filter(o => o.id !== createdCase.id)]
	selectedCase.value = createdCase
	linkCase(true)
}

/**
 * Imperative on purpose: `emit("merged")` clears the selection in the alerts list, which
 * unmounts this button (it only renders while unlinked alerts are selected) — a modal
 * declared in this template would vanish with it. The dialog provider outlives us.
 */
function showMergeSuccessDialog(caseEntity: Case, mergedCount: number) {
	const caseRoute = routeIncidentManagementCases(caseEntity.id)

	dialog.success({
		title: "Case created",
		content: () =>
			h("div", { class: "flex flex-col gap-2" }, [
				h("span", [
					"Case ",
					h("strong", `#${caseEntity.id} — ${caseEntity.case_name}`),
					" has been created and ",
					h("strong", `${mergedCount} alert${mergedCount === 1 ? "" : "s"}`),
					` ${mergedCount === 1 ? "has" : "have"} been merged into it.`
				])
			]),
		positiveText: "Open case",
		negativeText: "Close",
		onPositiveClick: () => {
			caseRoute.navigate()
		}
	})
}

function linkCase(createdHere = false) {
	if (selectedCase.value?.id) {
		merging.value = true
		const targetCase = selectedCase.value

		Api.incidentManagement.cases
			.multiLinkCase(
				alerts.map(o => o.id),
				targetCase.id
			)
			.then(res => {
				if (res.data.success) {
					closeDialog()
					mode.value = "existing"

					for (const alert of alerts) {
						const caseId = res.data.case_alert_links.find(o => o.alert_id === alert.id)?.case_id || 0
						const caseData = linkableCases.value.find(o => o.id === caseId) || null
						updateAlert({
							...alert,
							linked_cases: [
								{
									id: caseId,
									case_name: caseData?.case_name || "",
									case_description: caseData?.case_description || "",
									case_creation_time: caseData?.case_creation_time || new Date(),
									assigned_to: caseData?.assigned_to || null,
									case_status: caseData?.case_status || null,
									customer_code: caseData?.customer_code || null,
									comments: caseData?.comments || []
								}
							]
						})
					}

					if (createdHere) {
						showMergeSuccessDialog(targetCase, alerts.length)
						// Server truth for the next merge: the case was created outside the
						// list's own fetch, and a stale list is exactly what the analyst
						// reported as "the case I just created isn't there".
						getCasesList()
					} else {
						message.success(res.data?.message || "Case linked successfully")
					}

					emit("merged")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			})
			.finally(() => {
				merging.value = false
			})
	}
}
</script>
