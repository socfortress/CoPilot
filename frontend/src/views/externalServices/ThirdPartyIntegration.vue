<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeThirdPartyIntegration().navigate()">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to integrations
		</n-button>

		<IntegrationDetails v-if="integrationId != null" :integration-id :embedded="false" />
		<n-empty v-else description="Invalid integration ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import IntegrationDetails from "@/components/integrations/IntegrationDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeThirdPartyIntegration } = useNavigation()

const BackIcon = "carbon:arrow-left"

const integrationId = useRouteIdParam("id")
</script>
