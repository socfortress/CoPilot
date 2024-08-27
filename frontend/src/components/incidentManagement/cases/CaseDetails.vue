<template>
	<n-spin :show="loading" class="flex flex-col grow" content-class="flex flex-col grow">
		<n-tabs
			type="line"
			animated
			:tabs-padding="24"
			v-if="caseEntity"
			class="grow"
			pane-wrapper-class="flex flex-col grow"
		>
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex flex-col grow">
				<div class="pt-1">
					<CaseOverview :caseData="caseEntity" @updated="updateCase($event)" @deleted="emit('deleted')" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Alerts" tab="Alerts" display-directive="show:lazy">
				<div class="p-7 pt-4 flex flex-col gap-2">
					<AlertItem
						v-for="alert of caseEntity.alerts"
						:key="alert.id"
						:alertData="alert"
						embedded
						@deleted="getCase(caseEntity.id)"
						@updated="getCase(caseEntity.id)"
					/>
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import { defineAsyncComponent, onBeforeMount, ref, toRefs } from "vue"
import { NTabs, NTabPane, NSpin, useMessage } from "naive-ui"
import _clone from "lodash/cloneDeep"
import Api from "@/api"
import type { Case } from "@/types/incidentManagement/cases.d"

const CaseOverview = defineAsyncComponent(() => import("./CaseOverview.vue"))
const AlertItem = defineAsyncComponent(() => import("../alerts/AlertItem.vue"))

const props = defineProps<{
	caseData?: Case
	caseId?: number
}>()
const { caseData, caseId } = toRefs(props)

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Case): void
}>()

const message = useMessage()
const loading = ref(false)
const caseEntity = ref<Case | null>(null)

function updateCase(updatedCase: Case) {
	caseEntity.value = updatedCase
	emit("updated", updatedCase)
}

function getCase(caseId: number) {
	loading.value = true

	Api.incidentManagement
		.getCase(caseId)
		.then(res => {
			if (res.data.success) {
				caseEntity.value = res.data?.cases?.[0] || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	if (caseId.value) {
		getCase(caseId.value)
	} else if (caseData.value) {
		caseEntity.value = _clone(caseData.value)
	}
})
</script>
