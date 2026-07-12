<template>
	<n-tabs type="line" animated :tabs-padding="fullWidth ? 0 : 24">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
			<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
				<GroupDetails :entity="entity" />
			</div>
		</n-tab-pane>
		<n-tab-pane
			name="Software"
			:tab="`Software (${entity?.software?.length || 0})`"
			display-directive="show:lazy"
		>
			<div :class="fullWidth ? 'p-0' : 'px-6 pt-3 pb-6'">
				<SoftwareList v-if="entity" :list="entity.software" />
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
import type { MitreGroupDetails } from "@/types/mitre"
import { NTabPane, NTabs } from "naive-ui"
import SoftwareList from "../Software/SoftwareList.vue"
import TechniquesList from "../Technique/TechniquesList.vue"
import GroupDetails from "./GroupDetails.vue"

defineProps<{
	entity?: MitreGroupDetails
	fullWidth?: boolean
}>()
</script>
