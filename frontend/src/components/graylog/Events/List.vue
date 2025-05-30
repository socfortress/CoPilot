<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="!cursor-help">
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
		<div class="my-3 flex min-h-52 flex-col gap-2">
			<template v-if="itemsPaginated.length">
				<EventItem
					v-for="event of itemsPaginated"
					:key="event.id"
					:event="event"
					:highlight="event.id === highlight"
				/>
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { SelectMixedOption } from "naive-ui/es/select/src/interface"
import type { EventDefinition } from "@/types/graylog/event-definition.d"
import { NButton, NEmpty, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, nextTick, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import EventItem from "./Item.vue"

const props = defineProps<{ highlight: string | null | undefined }>()

const emit = defineEmits<{
	(e: "loaded", value: EventDefinition[]): void
}>()

const { highlight } = toRefs(props)

const InfoIcon = "carbon:information"

const message = useMessage()
const total = ref(0)
const loading = ref(false)
const events = ref<EventDefinition[]>([])
const priorities = computed<SelectMixedOption[]>(() =>
	[...new Set(events.value.map(o => o.priority))].map(o => ({
		label: `Priority ${o.toString()}`,
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

function scrollToItem(id: string) {
	const element = document.getElementById(`event-${id}`)
	const scrollContent = document.querySelector("#main > .n-scrollbar > .n-scrollbar-container") as HTMLElement

	if (element && scrollContent) {
		const wrap: HTMLElement = scrollContent
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent?.scrollTo({ top: middle, behavior: "smooth" })
	}
}

function getData() {
	loading.value = true

	Api.graylog
		.getEventDefinitions()
		.then(res => {
			if (res.data.success) {
				events.value = res.data.event_definitions || []
				total.value = events.value.length || 0
				emit("loaded", events.value)

				nextTick(() => {
					setTimeout(() => {
						if (highlight.value) {
							scrollToItem(highlight.value)
						}
					}, 300)
				})
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

watch(highlight, val => {
	if (val) {
		nextTick(() => {
			setTimeout(() => {
				scrollToItem(val)
			})
		})
	}
})

onBeforeMount(() => {
	getData()
})
</script>
