<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span v-if="sourceName" class="truncate text-lg font-semibold">{{ sourceName }}</span>
		</div>

		<SourceConfigurationDetails
			v-if="sourceName"
			:key="sourceName"
			deletable
			:source="sourceName"
			@deleted="onDeleted"
		/>
		<n-empty v-else description="Invalid source name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import SourceConfigurationDetails from "@/components/incidentManagement/sources/SourceConfigurationDetails.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeIncidentManagementSources } = useNavigation()

const BackIcon = "carbon:arrow-left"

const sourceName = computed(() => {
	const raw = route.params.source
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeIncidentManagementSources().navigate()
}

function onDeleted() {
	routeIncidentManagementSources().navigate()
}
</script>
