<template>
	<div class="alerts-filters flex flex-col gap-2">
		<div class="flex gap-2">
			<n-form-item label="Alerts for group" class="basis-1/2">
				<n-select v-model:value="filters.size" :options="sizeOptions" />
			</n-form-item>
			<n-form-item label="Time range" class="basis-1/2">
				<n-select v-model:value="filters.timerange" :options="timerangeOptions" />
			</n-form-item>
		</div>

		<div class="flex justify-end">
			<n-button strong secondary type="primary" @click="search()">
				<template #icon>
					<Icon :name="SearchIcon"></Icon>
				</template>
				Search
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, toRefs } from "vue"
import { NSelect, NButton, NFormItem } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useStorage } from "@vueuse/core"
import type { AlertsQueryTimeRange, GraylogAlertsQuery } from "@/api/endpoints/alerts"

const props = defineProps<{ filters: Partial<GraylogAlertsQuery> }>()
const { filters } = toRefs(props)

const emit = defineEmits<{
	(e: "search"): void
}>()

const SearchIcon = "carbon:search"

const timerangeOptions: { label: string; value: AlertsQueryTimeRange }[] = [
	{ label: "1 Hour", value: "1h" },
	{ label: "6 Hours", value: "6h" },
	{ label: "12 Hours", value: "12h" },
	{ label: "1 Day", value: "1d" },
	{ label: "2 Day", value: "2d" },
	{ label: "5 Day", value: "5d" },
	{ label: "1 Week", value: "1w" },
	{ label: "2 Week", value: "2w" },
	{ label: "3 Week", value: "3w" },
	{ label: "4 Week", value: "4w" }
]

const sizeOptions = [
	{ label: "1 Alert", value: 1 },
	{ label: "5 Alert", value: 5 },
	{ label: "10 Alert", value: 10 },
	{ label: "20 Alert", value: 20 }
]

const sizeDefault = useStorage<number>("alert-size-default", sizeOptions[2].value, localStorage)
const timerangeDefault = useStorage<AlertsQueryTimeRange>(
	"alert-timerange-default",
	timerangeOptions[3].value,
	localStorage
)

function search() {
	emit("search")
	timerangeDefault.value = filters.value.timerange
	sizeDefault.value = filters.value.size
}

onBeforeMount(() => {
	if (!filters.value.timerange) {
		filters.value.timerange = timerangeDefault.value
	}
	if (!filters.value.size) {
		filters.value.size = sizeDefault.value
	}
})
</script>
