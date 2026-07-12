<template>
	<n-tabs type="line" animated :tabs-padding="fullWidth ? 0 : 24">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
			<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
				<MitigationDetails :entity="entity" />
			</div>
		</n-tab-pane>
		<n-tab-pane
			name="Techniques"
			:tab="`Techniques (${entity?.techniques?.length || 0})`"
			display-directive="show:lazy"
		>
			<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
				<TechniquesList v-if="entity" :list="entity.techniques" />
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { MitreMitigationDetails } from "@/types/mitre"
import { NTabPane, NTabs } from "naive-ui"
import TechniquesList from "../Technique/TechniquesList.vue"
import MitigationDetails from "./MitigationDetails.vue"

defineProps<{
	entity?: MitreMitigationDetails
	fullWidth?: boolean
}>()
</script>
