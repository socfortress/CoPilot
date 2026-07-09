<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<AlertDetails v-if="alertId" :alert-id full-width @deleted="onDeleted" />
		<n-empty v-else description="Invalid alert ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import AlertDetails from "@/components/incidentManagement/alerts/AlertDetails.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeIncidentManagementAlerts } = useNavigation()

const BackIcon = "carbon:arrow-left"

const alertId = computed(() => {
	const raw = route.params.id
	const value = Array.isArray(raw) ? raw[0] : raw
	const parsed = Number.parseInt(value, 10)
	return Number.isFinite(parsed) ? parsed : null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeIncidentManagementAlerts().navigate()
}

function onDeleted() {
	routeIncidentManagementAlerts().navigate()
}
</script>
