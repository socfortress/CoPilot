<template>
	<div class="alert-actions flex gap-4 justify-end">
		<n-button
			:loading="loadingDecommission"
			type="error"
			v-if="networkConnector.deployed"
			:size="size"
			secondary
			@click="decommissionNetworkConnector()"
		>
			<template #icon><Icon :name="DecommissionIcon"></Icon></template>
			Decommission
		</n-button>

		<n-button
			:loading="loadingFortinetProvision"
			type="success"
			v-if="isFortinet && !networkConnector.deployed"
			:size="size"
			secondary
			@click="showFortinetForm = true"
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

		<n-modal
			v-model:show="showFortinetForm"
			preset="card"
			:style="{ maxWidth: 'min(420px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="Fortinet options"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<n-spin v-model:show="loadingFortinetProvision">
				<FortinetForm v-model:options="fortinetOptions" />
			</n-spin>

			<template #footer>
				<div class="flex justify-end">
					<n-button
						:loading="loadingFortinetProvision"
						@click="fortinetProvision()"
						type="success"
						secondary
						:disabled="!isFortinetFormValid"
					>
						<template #icon><Icon :name="DeployIcon"></Icon></template>
						Deploy
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, NModal, NSpin, useDialog, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { computed, h, ref } from "vue"
import { watch } from "vue"
import type { Size } from "naive-ui/es/button/src/interface"
import type { CustomerNetworkConnector } from "@/types/networkConnectors"
import type { FortinetProvision } from "@/api/networkConnectors"
import FortinetForm, { type FortinetModel } from "./provisions/FortinetForm.vue"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "deployed"): void
	(e: "decommissioned"): void
	(e: "deleted"): void
}>()

const { networkConnector, hideDeleteButton, size } = defineProps<{
	networkConnector: CustomerNetworkConnector
	hideDeleteButton?: boolean
	size?: Size
}>()

const DeployIcon = "carbon:deploy"
const DeleteIcon = "ph:trash"
const DecommissionIcon = "carbon:delete"

const dialog = useDialog()
const message = useMessage()
const loadingFortinetProvision = ref(false)
const loadingDelete = ref(false)
const loadingDecommission = ref(false)
const loading = computed(() => loadingFortinetProvision.value || loadingDecommission.value || loadingDelete.value)

const serviceName = computed(() => networkConnector.network_connector_service_name)
const customerCode = computed(() => networkConnector.customer_code)
const isFortinet = computed(() => serviceName.value === "Fortinet")

const showFortinetForm = ref(false)

const fortinetOptions = ref<FortinetModel>({
	protocol: "tcp",
	hot_data_retention: 1,
	index_replicas: 0
})

const isFortinetFormValid = computed(() => {
	if (fortinetOptions.value.hot_data_retention === null) {
		return false
	}
	if (fortinetOptions.value.index_replicas === null) {
		return false
	}
	return true
})

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function fortinetProvision() {
	loadingFortinetProvision.value = true

	const options: FortinetProvision = {
		tcp_enabled: fortinetOptions.value.protocol === "tcp",
		udp_enabled: fortinetOptions.value.protocol === "udp",
		hot_data_retention: fortinetOptions.value.hot_data_retention,
		index_replicas: fortinetOptions.value.index_replicas
	}

	Api.networkConnectors
		.fortinetProvision(customerCode.value, serviceName.value, options)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Fortinet customer provisioned successfully.")
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

function decommissionNetworkConnector() {
	loadingDecommission.value = true

	Api.networkConnectors
		.decommissionNetworkConnector(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("decommissioned")
				message.success(res.data?.message || "Customer Network Connector successfully decommissioned.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDecommission.value = false
		})
}
</script>
