<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeNetworkConnector().navigate()">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to network connectors
		</n-button>

		<NetworkConnectorDetails v-if="connectorId != null" :connector-id :embedded="false" />
		<n-empty v-else description="Invalid network connector ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import NetworkConnectorDetails from "@/components/networkConnectors/NetworkConnectorDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeNetworkConnector } = useNavigation()

const BackIcon = "carbon:arrow-left"

const connectorId = useRouteIdParam("id")
</script>
