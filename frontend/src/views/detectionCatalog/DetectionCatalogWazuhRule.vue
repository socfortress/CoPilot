<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeDetectionCatalogWazuhRule()" />

		<WazuhRuleDetail v-if="ruleId != null" :rule-id />
		<n-empty v-else description="Invalid Wazuh rule ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import WazuhRuleDetail from "@/components/detectionCatalog/WazuhRuleDetail.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeDetectionCatalogWazuhRule } = useNavigation()

const ruleId = useRouteIdParam("id")
</script>
