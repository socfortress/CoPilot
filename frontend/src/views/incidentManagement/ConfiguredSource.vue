<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementSources())">
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
import Icon from "@/components/common/Icon.vue"
import SourceConfigurationDetails from "@/components/incidentManagement/sources/SourceConfigurationDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementSources } = useNavigation()

const BackIcon = "carbon:arrow-left"

const sourceName = useRouteParam("source")

function onDeleted() {
	routeIncidentManagementSources().navigate()
}
</script>
