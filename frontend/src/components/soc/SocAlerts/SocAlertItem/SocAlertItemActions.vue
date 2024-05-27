<template>
	<div class="soc-alert-actions flex flex-col gap-2 justify-center">
		<n-button v-if="existCase" type="success" secondary @click="openSocCase()" :size="size">
			<template #icon><Icon :name="ViewIcon"></Icon></template>
			View SOC Case
		</n-button>
		<n-button
			:loading="loadingCaseCreation"
			type="warning"
			secondary
			@click="createCase()"
			:size="size"
			v-else-if="alertId"
		>
			<template #icon><Icon :name="DangerIcon"></Icon></template>
			Create SOC Case
		</n-button>
		<n-button
			:loading="loadingAlertDelete"
			:size="size"
			type="error"
			secondary
			@click="handleDelete()"
			v-if="alertId"
		>
			<template #icon><Icon :name="DeleteIcon"></Icon></template>
			Delete
		</n-button>

		<n-modal
			v-model:show="showSocCaseDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(250px, 90vh)', overflow: 'hidden' }"
			:title="`SOC Case: #${caseId}`"
			:bordered="false"
			segmented
		>
			<div class="h-full w-full flex items-center justify-center">
				<SocCaseItem
					v-if="caseId"
					:caseId="caseId"
					embedded
					hideSocAlertLink
					hide-soc-case-action
					class="w-full"
				/>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, useDialog, useMessage, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { computed, ref, watch } from "vue"
import SocCaseItem from "@/components/soc/SocCases/SocCaseItem.vue"
import type { Size } from "naive-ui/es/button/src/interface"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "caseCreated", value: string | number): void
	(e: "deleted"): void
	(e: "startDeleting"): void
}>()

const { alertId, caseId, size } = defineProps<{
	alertId?: string | number | null
	caseId?: string | number | null
	size?: Size
}>()

const DeleteIcon = "ph:trash"
const DangerIcon = "majesticons:exclamation-line"
const ViewIcon = "iconoir:eye-alt"

const dialog = useDialog()
const message = useMessage()
const showSocCaseDetails = ref(false)
const loadingCaseCreation = ref(false)
const loadingAlertDelete = ref(false)
const loading = computed(() => loadingCaseCreation.value || loadingAlertDelete.value)

const existCase = ref(!!caseId)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function openSocCase() {
	showSocCaseDetails.value = true
}

function createCase() {
	if (alertId) {
		loadingCaseCreation.value = true

		Api.soc
			.createCase(alertId.toString())
			.then(res => {
				if (res.data.success) {
					existCase.value = true
					emit("caseCreated", res.data.case.case_id)
					message.success(res.data?.message || "SOC Case created.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingCaseCreation.value = false
			})
	}
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: "This will delete the alert are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteAlert()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteAlert() {
	if (alertId) {
		loadingAlertDelete.value = true
		emit("startDeleting")

		Api.soc
			.deleteAlert(alertId.toString())
			.then(res => {
				if (res.data.success) {
					message.success(res.data?.message || "SOC Alert deleted.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				emit("deleted")
				loadingAlertDelete.value = false
			})
	}
}
</script>
