<template>
	<div class="page">
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="messages" tab="Messages" display-directive="show:lazy">
				<Messages />
			</n-tab-pane>
			<n-tab-pane name="alerts" tab="Alerts" display-directive="show:lazy">
				<Alerts @click-event="gotoEventsPage($event)" />
			</n-tab-pane>
			<n-tab-pane name="events" tab="Events" display-directive="show:lazy">
				<Events :highlight="highlightEvent" @loaded="events = $event" />
			</n-tab-pane>
			<n-tab-pane name="streams" tab="Streams" display-directive="show:lazy">
				<Streams />
			</n-tab-pane>
			<n-tab-pane name="provisioning" tab="Alert Provisioning" display-directive="show:lazy">
				<MonitoringAlerts :events-list="events" />
			</n-tab-pane>
			<template #suffix>
				<n-button ghost type="primary" size="small" @click="showInputDrawer = true">Inputs</n-button>
			</template>
		</n-tabs>

		<n-drawer
			v-model:show="showInputDrawer"
			:width="700"
			style="max-width: 90vw"
			:trap-focus="false"
			display-directive="show"
		>
			<n-drawer-content title="Inputs" closable body-content-style="padding:0">
				<Inputs />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import { NButton, NDrawer, NDrawerContent, NTabPane, NTabs } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

const Messages = defineAsyncComponent(() => import("@/components/graylog/Messages/List.vue"))
const Alerts = defineAsyncComponent(() => import("@/components/graylog/Alerts/List.vue"))
const Events = defineAsyncComponent(() => import("@/components/graylog/Events/List.vue"))
const Streams = defineAsyncComponent(() => import("@/components/graylog/Streams/List.vue"))
const MonitoringAlerts = defineAsyncComponent(() => import("@/components/graylog/MonitoringAlerts/List.vue"))
const Inputs = defineAsyncComponent(() => import("@/components/graylog/Inputs/List.vue"))

const tabsList = ["messages", "alerts", "events", "streams", "provisioning"]
const drawersList = ["inputs"]

const activeTab = ref<string | undefined>(tabsList[0])
const highlightEvent = ref<string | undefined>(undefined)
const showInputDrawer = ref(false)
const events = ref<EventDefinition[]>([])
const route = useRoute()
const router = useRouter()

function gotoEventsPage(event_definition_id: string) {
	activeTab.value = "events"
	highlightEvent.value = event_definition_id
}

watch(activeTab, val => {
	router.replace({ hash: `#${val}` })
})

onBeforeMount(() => {
	const hash = route.hash ? route.hash.slice(1) : ""
	if (hash && tabsList.includes(hash)) {
		activeTab.value = hash
	}
	if (hash && drawersList.includes(hash)) {
		if (hash === "inputs") {
			showInputDrawer.value = true
		}
	}
})
</script>

<style lang="scss" scoped></style>
