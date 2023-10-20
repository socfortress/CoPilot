<template>
	<div class="page">
		<n-tabs type="line" animated>
			<n-tab-pane name="messages" tab="Messages">
				<Messages />
			</n-tab-pane>
			<n-tab-pane name="alerts" tab="Alerts">
				<Alerts />
			</n-tab-pane>
			<n-tab-pane name="events" tab="Events">events</n-tab-pane>
			<n-tab-pane name="streams" tab="Streams">streams</n-tab-pane>
			<n-tab-pane name="inputs" tab="Inputs">inputs</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup>
import { NTabs, NTabPane } from "naive-ui"
import Messages from "@/components/graylog/Messages/List.vue"
import Alerts from "@/components/graylog/Alerts/index.vue"
</script>

<style lang="scss" scoped></style>
