<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<n-button secondary size="small">
							<template #icon>
								<Icon :name="InfoIcon"></Icon>
							</template>
						</n-button>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ events.length }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="filters">filters...</div>
		</div>
		<div class="list my-3">
			<EventItem v-for="event of events" :key="event.id" :event="event" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NSpin, NPopover, NButton } from "naive-ui"
import EventItem from "./Item.vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import type { EventDefinition } from "@/types/graylog/event-definition.d"

const InfoIcon = "carbon:information"

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
