<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span class="truncate text-lg font-semibold">Create Source Configuration</span>
		</div>

		<SourceConfigurationWizard :disabled-sources="configuredSourcesList" full-width @submitted="onSubmitted" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SourceName } from "@/types/incidentManagement/sources"
import { NButton, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SourceConfigurationWizard from "@/components/incidentManagement/sources/SourceConfigurationWizard.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const BackIcon = "carbon:arrow-left"
const router = useRouter()
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

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeIncidentManagementSources().navigate()
}

function onSubmitted() {
	routeIncidentManagementSources().navigate()
}

onBeforeMount(() => {
	getConfiguredSources()
})
</script>
