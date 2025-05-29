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
		:title="`Select the case you want to merge ${alerts.length > 1 ? 'them' : 'it'} with :`"
		:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(540px, 90vh)', maxHeight: '80vh' }"
		content-class="flex flex-col overflow-hidden !px-2 !py-0"
		segmented
	>
		<n-spin
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

		<template #footer>
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
import type { Size } from "naive-ui/es/button/src/interface"
import type { Ref } from "vue"
import type { Alert } from "@/types/incidentManagement/alerts.d"
import type { Case } from "@/types/incidentManagement/cases.d"
import _orderBy from "lodash/orderBy"
import { NButton, NEmpty, NModal, NScrollbar, NSpin, useMessage } from "naive-ui"
import { inject, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CaseItem from "../cases/CaseItem.vue"

const { alerts, size } = defineProps<{ alerts: Alert[]; size?: Size }>()

const emit = defineEmits<{
	(e: "updated", value: Alert): void
	(e: "merged"): void
}>()

const MergeIcon = "carbon:ibm-cloud-direct-link-1-connect"
const message = useMessage()
const merging = ref(false)
const showMergeBox = ref(false)
const loadingCases = ref(false)
const linkableCases = inject<Ref<Case[]>>("linkable-cases", ref([]))
const selectedCase = ref<Case | null>(null)

watch(showMergeBox, val => {
	if (val && !linkableCases.value.length) {
		getCasesList()
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
		.getCasesList()
		.then(res => {
			if (res.data.success) {
				linkableCases.value = _orderBy(res.data?.cases || [], ["id"], ["desc"])
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCases.value = false
		})
}

function linkCase() {
	if (selectedCase.value?.id) {
		merging.value = true

		Api.incidentManagement.cases
			.multiLinkCase(
				alerts.map(o => o.id),
				selectedCase.value.id
			)
			.then(res => {
				if (res.data.success) {
					closeDialog()

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
									customer_code: caseData?.customer_code || null
								}
							]
						})
					}

					emit("merged")
					message.success(res.data?.message || "Case linked successfully")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				merging.value = false
			})
	}
}
</script>
