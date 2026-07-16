<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create Source Configuration" :back-route="routeIncidentManagementSources()" />

		<SourceConfigurationWizard :disabled-sources="configuredSourcesList" full-width @submitted="onSubmitted" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SourceName } from "@/types/incidentManagement/sources"
import { useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import SourceConfigurationWizard from "@/components/incidentManagement/sources/SourceConfigurationWizard.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const message = useMessage()
const { routeIncidentManagementSources } = useNavigation()
const configuredSourcesList = ref<SourceName[]>([])

function getConfiguredSources() {
	Api.incidentManagement.sources
		.getConfiguredSources()
		.then(res => {
			if (res.data.success) {
				configuredSourcesList.value = res.data?.sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
}

function onSubmitted() {
	routeIncidentManagementSources().navigate()
}

onBeforeMount(() => {
	getConfiguredSources()
})
</script>
