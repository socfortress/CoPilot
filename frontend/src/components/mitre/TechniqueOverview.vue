<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy">
			<div class="px-7 pb-7 pt-4">
				<TechniqueDetails :external-id />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Groups" tab="Groups" display-directive="show:lazy">
			<div class="px-7">Groups...</div>
		</n-tab-pane>
		<n-tab-pane name="Mitigations" tab="Mitigations" display-directive="show:lazy">
			<div class="px-7">Mitigations...</div>
		</n-tab-pane>
		<n-tab-pane name="Software" tab="Software" display-directive="show:lazy">
			<div class="px-7">Software...</div>
		</n-tab-pane>
		<n-tab-pane name="Tactics" tab="Tactics" display-directive="show:lazy">
			<div class="px-7">Tactics...</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import { NTabPane, NTabs } from "naive-ui"
import TechniqueDetails from "./TechniqueDetails.vue"

const { externalId } = defineProps<{
	externalId: string
}>()
</script>
