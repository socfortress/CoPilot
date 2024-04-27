<template>
	<div class="soc-case-actions flex flex-col gap-2 justify-center">
		<n-button
			v-if="isCaseClosed"
			:loading="loadingCaseReopen"
			:size="size"
			type="warning"
			secondary
			@click="reopenCase()"
		>
			<template #icon><Icon :name="OpenIcon"></Icon></template>
			Reopen
		</n-button>
		<n-button v-else :loading="loadingCaseClose" type="success" secondary :size="size" @click="closeCase()">
			<template #icon><Icon :name="CloseIcon"></Icon></template>
			Close
		</n-button>
		<n-button :loading="loadingCaseDelete" :size="size" type="error" secondary @click="handleDelete()">
			<template #icon><Icon :name="DeleteIcon"></Icon></template>
			Delete
		</n-button>
	</div>
</template>

<script setup lang="ts">
import { NButton, useDialog, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { computed, watch, ref } from "vue"
import { StateName, type SocCase, type SocCaseExt } from "@/types/soc/case.d"
import type { Size } from "naive-ui/es/button/src/interface"

const emit = defineEmits<{
	(e: "closed"): void
	(e: "reopened"): void
	(e: "deleted"): void
	(e: "startDeleting"): void
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const { caseData, size } = defineProps<{
	caseData: SocCase | SocCaseExt | null
	size?: Size
}>()

const DeleteIcon = "ph:trash"
const CloseIcon = "ph:circle-wavy-check"
const OpenIcon = "ph:circle-wavy-warning"

const dialog = useDialog()
const message = useMessage()
const loadingCaseClose = ref(false)
const loadingCaseReopen = ref(false)
const loadingCaseDelete = ref(false)
const loading = computed(() => loadingCaseClose.value || loadingCaseReopen.value || loadingCaseDelete.value)

const isCaseClosed = computed(() => caseData?.state_name === StateName.Closed)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function closeCase() {
	if (caseData?.case_id) {
		loadingCaseClose.value = true

		Api.soc
			.closeCase(caseData.case_id.toString())
			.then(res => {
				if (res.data.success) {
					emit("closed")
					message.success(res.data?.message || "SOC Case closed.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingCaseClose.value = false
			})
	}
}

function reopenCase() {
	if (caseData?.case_id) {
		loadingCaseReopen.value = true

		Api.soc
			.reopenCase(caseData.case_id.toString())
			.then(res => {
				if (res.data.success) {
					emit("reopened")
					message.success(res.data?.message || "SOC Case reopened.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingCaseReopen.value = false
			})
	}
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: "This will delete the case, are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteCase()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteCase() {
	if (caseData?.case_id) {
		loadingCaseDelete.value = true
		emit("startDeleting")

		Api.soc
			.deleteCase(caseData.case_id.toString())
			.then(res => {
				if (res.data.success) {
					message.success(res.data?.message || "SOC Case deleted.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				emit("deleted")
				loadingCaseDelete.value = false
			})
	}
}
</script>
