<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="sourceName || undefined" :back-route="routeIncidentManagementSources()" />

		<SourceConfigurationDetails
			v-if="sourceName"
			:key="sourceName"
			deletable
			:source="sourceName"
			@deleted="routeIncidentManagementSources().navigate()"
		/>
		<n-empty v-else description="Invalid source name" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import SourceConfigurationDetails from "@/components/incidentManagement/sources/SourceConfigurationDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeIncidentManagementSources } = useNavigation()

const sourceName = useRouteParam("source")
</script>
