<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeNetworkConnector()" />

		<NetworkConnectorDetails v-if="connectorId != null" :connector-id :embedded="false" />
		<n-empty v-else description="Invalid network connector ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import NetworkConnectorDetails from "@/components/networkConnectors/NetworkConnectorDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeNetworkConnector } = useNavigation()

const connectorId = useRouteIdParam("id")
</script>
