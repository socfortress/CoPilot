<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack(routeDetectionCatalogWazuhRule())">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<WazuhRuleDetail v-if="ruleId != null" :rule-id />
		<n-empty v-else description="Invalid Wazuh rule ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import WazuhRuleDetail from "@/components/detectionCatalog/WazuhRuleDetail.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeDetectionCatalogWazuhRule } = useNavigation()

const BackIcon = "carbon:arrow-left"

const ruleId = useRouteIdParam("id")
</script>
