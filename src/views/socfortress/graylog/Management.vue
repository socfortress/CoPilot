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
			<n-tab-pane name="streams" tab="Streams" display-directive="show:lazy">
				<Streams />
			</n-tab-pane>
			<template #suffix>
				<n-button ghost type="primary" size="small" @click="showInputDrawer = true">Inputs</n-button>
			</template>
		</n-tabs>

		<n-drawer v-model:show="showInputDrawer" :width="700" style="max-width: 90vw" :trap-focus="false">
			<n-drawer-content title="Inputs" closable body-content-style="padding:0">
				<Inputs />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup>
import { ref } from "vue"
import { NTabs, NTabPane, NButton, NDrawer, NDrawerContent } from "naive-ui"
import Messages from "@/components/graylog/Messages/List.vue"
import Alerts from "@/components/graylog/Alerts/List.vue"
import Events from "@/components/graylog/Events/List.vue"
import Streams from "@/components/graylog/Streams/List.vue"
import Inputs from "@/components/graylog/Inputs/List.vue"

const showInputDrawer = ref(false)
</script>

<style lang="scss" scoped></style>
