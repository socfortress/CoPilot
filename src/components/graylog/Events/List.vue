<template>
	<n-spin :show="loading">
		<div class="list">
			<EventItem v-for="event of events" :key="event.id" :event="event" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NSpin } from "naive-ui"
import EventItem from "./Item.vue"
import Api from "@/api"
import type { EventDefinition } from "@/types/graylog/event-definition.d"

const message = useMessage()
const loading = ref(false)
const events = ref<EventDefinition[]>([])

function getData() {
	loading.value = true

	Api.graylog
		.getEventDefinitions()
		.then(res => {
			if (res.data.success) {
				events.value = res.data.event_definitions || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
