<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<AlertDetails v-if="indexName && alertId" :index-name :alert-id />
		<n-empty v-else description="Invalid alert reference" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import AlertDetails from "@/components/alerts/AlertDetails.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeAlertsSiemSummary } = useNavigation()

const BackIcon = "carbon:arrow-left"

const indexName = computed(() => {
	const raw = route.params.indexName
	if (!raw) return null
	const value = Array.isArray(raw) ? raw[0] : raw
	return decodeURIComponent(value)
})

const alertId = computed(() => {
	const raw = route.params.alertId
	if (!raw) return null
	const value = Array.isArray(raw) ? raw[0] : raw
	return decodeURIComponent(value)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeAlertsSiemSummary(indexName.value ?? undefined).navigate()
}
</script>
