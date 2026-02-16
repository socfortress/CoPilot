<template>
	<div class="contents">
		<n-button
			v-if="networkConnector.deployed"
			:loading="loadingDecommission"
			type="error"
			:size="size"
			secondary
			@click.stop="decommissionNetworkConnector()"
		>
			<template #icon>
				<Icon :name="DecommissionIcon" />
			</template>
			Decommission
		</n-button>

		<n-button
			v-if="isFortinet && !networkConnector.deployed"
			:loading="loadingFortinetProvision"
			type="success"
			:size="size"
			secondary
			@click.stop="showFortinetForm = true"
		>
			<template #icon>
				<Icon :name="DeployIcon" />
			</template>
			Deploy
		</n-button>

		<n-button
			v-if="isSonicwall && !networkConnector.deployed"
			:loading="loadingSonicwallProvision"
			type="success"
			:size="size"
			secondary
			@click.stop="showSonicwallForm = true"
		>
			<template #icon>
				<Icon :name="DeployIcon" />
			</template>
			Deploy
		</n-button>

		<n-button
			v-if="isSentinelOne && !networkConnector.deployed"
			:loading="loadingSentinelOneProvision"
			type="success"
			:size="size"
			secondary
			@click.stop="showSentinelOneForm = true"
		>
			<template #icon>
				<Icon :name="DeployIcon" />
			</template>
			Deploy
		</n-button>

		<n-button
			v-if="!hideDeleteButton"
			:size="size"
			type="error"
			ghost
			:loading="loadingDelete"
			@click.stop="handleDelete"
		>
			<template #icon>
				<Icon :name="DeleteIcon" :size="15" />
			</template>
			Delete
		</n-button>

		<!-- Fortinet Modal -->
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
						type="success"
						secondary
						:disabled="!isFortinetFormValid"
						@click.stop="fortinetProvision()"
					>
						<template #icon>
							<Icon :name="DeployIcon" />
						</template>
						Deploy
					</n-button>
				</div>
			</template>
		</n-modal>

		<!-- SonicWall Modal -->
		<n-modal
			v-model:show="showSonicwallForm"
			preset="card"
			:style="{ maxWidth: 'min(420px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="SonicWall options"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<n-spin v-model:show="loadingSonicwallProvision">
				<SonicwallForm v-model:options="sonicwallOptions" />
			</n-spin>

			<template #footer>
				<div class="flex justify-end">
					<n-button
						:loading="loadingSonicwallProvision"
						type="success"
						secondary
						:disabled="!isSonicwallFormValid"
						@click.stop="sonicwallProvision()"
					>
						<template #icon>
							<Icon :name="DeployIcon" />
						</template>
						Deploy
					</n-button>
				</div>
			</template>
		</n-modal>

		<!-- SentinelOne Modal -->
		<n-modal
			v-model:show="showSentinelOneForm"
			preset="card"
			:style="{ maxWidth: 'min(420px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="SentinelOne options"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<n-spin v-model:show="loadingSentinelOneProvision">
				<SentinelOneForm v-model:options="sentinelOneOptions" />
			</n-spin>

			<template #footer>
				<div class="flex justify-end">
					<n-button
						:loading="loadingSentinelOneProvision"
						type="success"
						secondary
						:disabled="!isSentinelOneFormValid"
						@click.stop="sentinelOneProvision()"
					>
						<template #icon>
							<Icon :name="DeployIcon" />
						</template>
						Deploy
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { FortinetModel } from "./provisions/FortinetForm.vue"
import type { SentinelOneModel } from "./provisions/SentinelOneForm.vue"
import type { SonicWallModel } from "./provisions/SonicwallForm.vue"
import type { FortinetProvision, SentinelOneProvision, SonicwallProvision } from "@/api/endpoints/networkConnectors"
import type { CustomerNetworkConnector } from "@/types/networkConnectors.d"
import { NButton, NModal, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import FortinetForm from "./provisions/FortinetForm.vue"
import SentinelOneForm from "./provisions/SentinelOneForm.vue"
import SonicwallForm from "./provisions/SonicwallForm.vue"

const { networkConnector, hideDeleteButton, size } = defineProps<{
	networkConnector: CustomerNetworkConnector
	hideDeleteButton?: boolean
	size?: Size
}>()

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "deployed"): void
	(e: "decommissioned"): void
	(e: "deleted"): void
}>()

const DeployIcon = "carbon:deploy"
const DeleteIcon = "ph:trash"
const DecommissionIcon = "carbon:delete"

const dialog = useDialog()
const message = useMessage()
const loadingFortinetProvision = ref(false)
const loadingSonicwallProvision = ref(false)
const loadingSentinelOneProvision = ref(false)
const loadingDelete = ref(false)
const loadingDecommission = ref(false)
const loading = computed(
	() =>
		loadingFortinetProvision.value ||
		loadingSonicwallProvision.value ||
		loadingSentinelOneProvision.value ||
		loadingDecommission.value ||
		loadingDelete.value
)

const serviceName = computed(() => networkConnector.network_connector_service_name)
const customerCode = computed(() => networkConnector.customer_code)
const isFortinet = computed(() => serviceName.value === "Fortinet")
const isSonicwall = computed(() => serviceName.value === "Sonicwall")
const isSentinelOne = computed(() => serviceName.value === "Sentinelone")

const showFortinetForm = ref(false)
const showSonicwallForm = ref(false)
const showSentinelOneForm = ref(false)

const fortinetOptions = ref<FortinetModel>({
	protocol: "tcp",
	hot_data_retention: 1,
	index_replicas: 0
})

const sonicwallOptions = ref<SonicWallModel>({
	protocol: "tcp",
	hot_data_retention: 1,
	index_replicas: 0
})

const sentinelOneOptions = ref<SentinelOneModel>({
	protocol: "tls",
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

const isSonicwallFormValid = computed(() => {
	if (sonicwallOptions.value.hot_data_retention === null) {
		return false
	}
	if (sonicwallOptions.value.index_replicas === null) {
		return false
	}
	return true
})

const isSentinelOneFormValid = computed(() => {
	if (sentinelOneOptions.value.hot_data_retention === null) {
		return false
	}
	if (sentinelOneOptions.value.index_replicas === null) {
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
				showFortinetForm.value = false
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

function sonicwallProvision() {
	loadingSonicwallProvision.value = true

	const options: SonicwallProvision = {
		tcp_enabled: sonicwallOptions.value.protocol === "tcp",
		hot_data_retention: sonicwallOptions.value.hot_data_retention,
		index_replicas: sonicwallOptions.value.index_replicas
	}

	Api.networkConnectors
		.sonicwallProvision(customerCode.value, serviceName.value, options)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				showSonicwallForm.value = false
				message.success(res.data?.message || "SonicWall customer provisioned successfully.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingSonicwallProvision.value = false
		})
}

function sentinelOneProvision() {
	loadingSentinelOneProvision.value = true

	const options: SentinelOneProvision = {
		tls_enabled: sentinelOneOptions.value.protocol === "tls",
		hot_data_retention: sentinelOneOptions.value.hot_data_retention,
		index_replicas: sentinelOneOptions.value.index_replicas
	}

	Api.networkConnectors
		.sentineloneProvision(customerCode.value, serviceName.value, options)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				showSentinelOneForm.value = false
				message.success(res.data?.message || "SentinelOne customer provisioned successfully.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingSentinelOneProvision.value = false
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
