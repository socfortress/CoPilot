<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeThirdPartyIntegration()" />

		<IntegrationDetails v-if="integrationId != null" :integration-id :embedded="false" />
		<n-empty v-else description="Invalid integration ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import IntegrationDetails from "@/components/integrations/IntegrationDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeThirdPartyIntegration } = useNavigation()

const integrationId = useRouteIdParam("id")
</script>
