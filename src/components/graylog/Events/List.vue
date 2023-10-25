<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-select
				v-model:value="prioritySelected"
				:options="priorities"
				clearable
				placeholder="Priority..."
				size="small"
				style="width: 110px"
			/>
		</div>
		<div class="list my-3">
			<EventItem v-for="event of itemsPaginated" :key="event.id" :event="event" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NPopover, NButton, NSelect } from "naive-ui"
import EventItem from "./Item.vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import type { SelectMixedOption } from "naive-ui/es/select/src/interface"

const InfoIcon = "carbon:information"

const message = useMessage()
const total = ref(0)
const loading = ref(false)
const events = ref<EventDefinition[]>([])
const priorities = computed<SelectMixedOption[]>(() =>
	[...new Set(events.value.map(o => o.priority))].map(o => ({
		label: "Priority " + o.toString(),
		value: o
	}))
)
const prioritySelected = ref<null | number>(null)

const itemsPaginated = computed(() => {
	return events.value.filter(o => {
		if (!prioritySelected.value) {
			return true
		} else {
			return o.priority === prioritySelected.value
		}
	})
})

function getData() {
	loading.value = true

	Api.graylog
		.getEventDefinitions()
		.then(res => {
			if (res.data.success) {
				events.value = res.data.event_definitions || []
				total.value = events.value.length || 0
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
