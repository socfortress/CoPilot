<template>
	<div class="alert-actions flex gap-4 justify-end">
		<n-button
			v-if="isOffice365 && !integration.deployed"
			:loading="loadingOffice365Provision"
			@click="office365Provision()"
			type="success"
			:size="size"
			secondary
		>
			<template #icon><Icon :name="DeployIcon"></Icon></template>
			Deploy
		</n-button>

		<n-button
			v-if="isMimecast && !integration.deployed"
			:loading="loadingMimecastProvision"
			@click="mimecastProvision()"
			type="success"
			:size="size"
			secondary
		>
			<template #icon><Icon :name="DeployIcon"></Icon></template>
			Deploy
		</n-button>

		<n-button
			v-if="isCrowdstrike && !integration.deployed"
			:loading="loadingCrowdstrikeProvision"
			@click="crowdstrikeProvision()"
			type="success"
			:size="size"
			secondary
		>
			<template #icon><Icon :name="DeployIcon"></Icon></template>
			Deploy
		</n-button>

		<n-button
			v-if="isDuo && !integration.deployed"
			:loading="loadingDuoProvision"
			@click="duoProvision()"
			type="success"
			:size="size"
			secondary
		>
			<template #icon><Icon :name="DeployIcon"></Icon></template>
			Deploy
		</n-button>

		<n-button
			:size="size"
			type="error"
			ghost
			@click="handleDelete"
			:loading="loadingDelete"
			v-if="!hideDeleteButton"
		>
			<template #icon>
				<Icon :name="DeleteIcon" :size="15"></Icon>
			</template>
			Delete
		</n-button>
	</div>
</template>

<script setup lang="ts">
import { NButton, useDialog, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { computed, h, ref } from "vue"
import { watch } from "vue"
import type { CustomerIntegration } from "@/types/integrations.d"
import type { Size } from "naive-ui/es/button/src/interface"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "deployed"): void
	(e: "deleted"): void
}>()

const { integration, hideDeleteButton, size } = defineProps<{
	integration: CustomerIntegration
	hideDeleteButton?: boolean
	size?: Size
}>()

const DeployIcon = "carbon:deploy"
const DeleteIcon = "ph:trash"

const dialog = useDialog()
const message = useMessage()
const loadingOffice365Provision = ref(false)
const loadingMimecastProvision = ref(false)
const loadingCrowdstrikeProvision = ref(false)
const loadingDuoProvision = ref(false)
const loadingDelete = ref(false)
const loading = computed(
	() =>
		loadingOffice365Provision.value ||
		loadingMimecastProvision.value ||
		loadingCrowdstrikeProvision.value ||
		loadingDuoProvision.value ||
		loadingDelete.value
)

const serviceName = computed(() => integration.integration_service_name)
const customerCode = computed(() => integration.customer_code)
const isOffice365 = computed(() => serviceName.value === "Office365")
const isMimecast = computed(() => serviceName.value === "Mimecast")
const isCrowdstrike = computed(() => serviceName.value === "Crowdstrike")
const isDuo = computed(() => serviceName.value === "DUO")

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function office365Provision() {
	loadingOffice365Provision.value = true

	Api.integrations
		.office365Provision(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Customer integration successfully deployed.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingOffice365Provision.value = false
		})
}

function mimecastProvision() {
	loadingMimecastProvision.value = true

	Api.integrations
		.mimecastProvision(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Customer integration successfully deployed.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingMimecastProvision.value = false
		})
}

function crowdstrikeProvision() {
	loadingCrowdstrikeProvision.value = true

	Api.integrations
		.crowdstrikeProvision(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Customer integration successfully deployed.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCrowdstrikeProvision.value = false
		})
}

function duoProvision() {
	loadingDuoProvision.value = true

	Api.integrations
		.duoProvision(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Customer integration successfully deployed.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDuoProvision.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the integration: <strong>${serviceName.value}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteIntegration()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteIntegration() {
	loadingDelete.value = true

	Api.integrations
		.deleteIntegration(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deleted")
				message.success(res.data?.message || "Customer integration successfully deleted.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}
</script>
