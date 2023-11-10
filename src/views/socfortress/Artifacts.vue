<template>
	<div class="page">
		<n-tabs type="line" animated v-model:value="activeTab">
			<n-tab-pane name="artifacts" tab="Artifacts" display-directive="show:lazy">Artifacts...</n-tab-pane>
			<n-tab-pane name="collect" tab="Collect" display-directive="show:lazy">Collect...</n-tab-pane>
			<n-tab-pane name="command" tab="Command" display-directive="show:lazy">Command...</n-tab-pane>
			<n-tab-pane name="quarantine" tab="Quarantine" display-directive="show:lazy">Quarantine...</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { NTabs, NTabPane } from "naive-ui"

const activeTab = ref<string | undefined>(undefined)
</script>

<style lang="scss" scoped></style>
