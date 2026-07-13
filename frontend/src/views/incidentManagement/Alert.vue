<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<div class="flex min-w-0 items-start gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="alert" class="flex min-w-0 flex-col gap-0.5 pt-1">
				<span class="truncate text-lg font-semibold">{{ alert.alert_name }}</span>
				<div class="flex items-center gap-2">
					<span class="text-secondary font-mono text-sm">#{{ alert.id }}</span>
					<span class="text-secondary text-sm">{{ alert.source }}</span>
				</div>
			</div>
		</div>

		<AlertDetails
			v-if="alertId"
			:key="alertId"
			:alert-id
			class="grow"
			full-width
			@loaded="alert = $event"
			@updated="alert = $event"
			@deleted="onDeleted"
		/>
		<n-empty v-else description="Invalid alert ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import AlertDetails from "@/components/incidentManagement/alerts/AlertDetails.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeIncidentManagementAlerts } = useNavigation()

const BackIcon = "carbon:arrow-left"
const alert = ref<Alert | null>(null)

const alertId = computed(() => {
	const raw = route.params.id
	const value = Array.isArray(raw) ? raw[0] : raw
	const parsed = Number.parseInt(value, 10)
	return Number.isFinite(parsed) ? parsed : null
})

watch(alertId, () => {
	alert.value = null
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
