<template>
	<div class="alert-actions flex gap-4 justify-end">
		<n-button v-if="isDeployEnabled" :loading="loading" @click="provision()" type="success" :size="size" secondary>
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
import { computed, h, ref, watch } from "vue"
import { NButton, useDialog, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import type { CustomerIntegration } from "@/types/integrations.d"
import type { Size } from "naive-ui/es/button/src/interface"
import type { ApiCommonResponse } from "@/types/common"

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

const loadingProvision = ref(false)
const loadingDelete = ref(false)
const loading = computed(() => loadingProvision.value || loadingDelete.value)
const serviceName = computed(() => integration.integration_service_name)
const customerCode = computed(() => integration.customer_code)
const isOffice365 = computed(() => serviceName.value === "Office365")
const isMimecast = computed(() => serviceName.value === "Mimecast")
const isCrowdstrike = computed(() => serviceName.value === "Crowdstrike")
const isDuo = computed(() => serviceName.value === "DUO")
const isDarktrace = computed(() => serviceName.value === "Darktrace")
const isDeployEnabled = computed(
	() =>
		(isOffice365.value || isMimecast.value || isCrowdstrike.value || isDuo.value || isDarktrace.value) &&
		!integration.deployed
)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function provision() {
	let apiCall: Promise<ApiCommonResponse> | null = null

	if (isOffice365.value) {
		apiCall = Api.integrations.office365Provision(customerCode.value, serviceName.value)
	}
	if (isMimecast.value) {
		apiCall = Api.integrations.mimecastProvision(customerCode.value, serviceName.value)
	}
	if (isCrowdstrike.value) {
		apiCall = Api.integrations.crowdstrikeProvision(customerCode.value, serviceName.value)
	}
	if (isDuo.value) {
		apiCall = Api.integrations.duoProvision(customerCode.value, serviceName.value)
	}
	if (isDarktrace.value) {
		apiCall = Api.integrations.darktraceProvision(customerCode.value, serviceName.value)
	}

	if (!apiCall) {
		return
	}

	loadingProvision.value = true

	apiCall
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
			loadingProvision.value = false
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
