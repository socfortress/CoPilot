<template>
	<div class="alert-actions flex gap-4 justify-end">
		<n-button
			v-if="isFortinet && !networkConnector.deployed"
			:loading="loadingFortinetProvision"
			@click="fortinetProvision()"
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
import type { Size } from "naive-ui/es/button/src/interface"
import type { CustomerNetworkConnector } from "@/types/networkConnectors"
import type { FortinetProvision } from "@/api/networkConnectors"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "deployed"): void
	(e: "deleted"): void
}>()

const { networkConnector, hideDeleteButton, size } = defineProps<{
	networkConnector: CustomerNetworkConnector
	hideDeleteButton?: boolean
	size?: Size
}>()

const DeployIcon = "carbon:deploy"
const DeleteIcon = "ph:trash"

const dialog = useDialog()
const message = useMessage()
const loadingFortinetProvision = ref(false)
const loadingDelete = ref(false)
const loading = computed(() => loadingFortinetProvision.value || loadingDelete.value)

const serviceName = computed(() => networkConnector.network_connector_service_name)
const customerCode = computed(() => networkConnector.customer_code)
const isFortinet = computed(() => serviceName.value === "Fortinet")

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function fortinetProvision() {
	loadingFortinetProvision.value = true

	const payload: FortinetProvision = {
		tcp_enabled: true,
		udp_enabled: true,
		hot_data_retention: 1,
		index_replicas: 1
	}

	Api.networkConnectors
		.fortinetProvision(customerCode.value, serviceName.value, payload)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Customer Network Connector successfully deployed.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingFortinetProvision.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the Network Connector: <strong>${serviceName.value}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteNetworkConnector()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteNetworkConnector() {
	loadingDelete.value = true

	Api.networkConnectors
		.deleteNetworkConnector(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deleted")
				message.success(res.data?.message || "Customer Network Connector successfully deleted.")
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
