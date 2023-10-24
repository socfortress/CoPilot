<template>
	<div class="page">
		<n-tabs type="line" animated>
			<n-tab-pane name="messages" tab="Messages" display-directive="show:lazy">
				<Messages />
			</n-tab-pane>
			<n-tab-pane name="alerts" tab="Alerts" display-directive="show:lazy">
				<Alerts />
			</n-tab-pane>
			<n-tab-pane name="events" tab="Events" display-directive="show:lazy">
				<Events />
			</n-tab-pane>
			<n-tab-pane name="streams" tab="Streams">
				<Streams />
			</n-tab-pane>
			<template #suffix>
				<n-button secondary type="primary" size="small">Inputs</n-button>
			</template>
		</n-tabs>
	</div>
</template>

<script setup>
import { NTabs, NTabPane, NButton } from "naive-ui"
import Messages from "@/components/graylog/Messages/List.vue"
import Alerts from "@/components/graylog/Alerts/List.vue"
import Events from "@/components/graylog/Events/List.vue"
import Streams from "@/components/graylog/Streams/List.vue"
</script>

<style lang="scss" scoped></style>
