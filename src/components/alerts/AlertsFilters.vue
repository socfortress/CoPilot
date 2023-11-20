<template>
	<div class="alerts-filters flex flex-col gap-2">
		<div class="flex gap-2">
			<n-form-item label="Filter key/value" class="grow">
				<n-input-group>
					<n-select
						v-model:value="filters.alertField"
						:options="alertFieldOptions"
						filterable
						clearable
						tag
						:render-tag="renderFieldTag"
						:render-label="renderFieldLabel"
						placeholder="Alert Field"
						class="basis-1/2"
					>
						<template #action>
							<n-button @click="clearFieldsHistory()" size="tiny" quaternary class="!w-full">
								<template #icon>
									<Icon :name="ClearIcon"></Icon>
								</template>
								Clear history
							</n-button>
						</template>
						<template #empty>
							<n-empty
								description="Empty Field history"
								class="text-center justify-center h-48"
							></n-empty>
						</template>
					</n-select>
					<n-input v-model:value="filters.alertValue" clearable placeholder="Field value" class="basis-1/2" />
				</n-input-group>
			</n-form-item>
		</div>
		<slot />

		<div class="flex gap-2">
			<n-form-item label="Alerts for group" class="basis-1/2">
				<n-select v-model:value="filters.maxAlerts" :options="maxAlertsOptions" />
			</n-form-item>
			<n-form-item label="Time range" class="basis-1/2">
				<n-select v-model:value="filters.timerange" :options="timerangeOptions" />
			</n-form-item>
		</div>

		<div class="flex justify-end">
			<n-button strong secondary type="primary" @click="emit('search')">
				<template #icon>
					<Icon :name="SearchIcon"></Icon>
				</template>
				Search
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, toRefs, watch, type VNodeChild, h } from "vue"
import { NSelect, NButton, NInput, NInputGroup, NEmpty, NFormItem, type SelectOption } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useStorage } from "@vueuse/core"
import _uniqBy from "lodash/uniqBy"
import type { AlertsQueryTimeRange, AlertsSummaryQuery } from "@/api/alerts"

const props = defineProps<{ filters: AlertsSummaryQuery }>()
const { filters } = toRefs(props)

const emit = defineEmits<{
	(e: "search"): void
}>()

const ClearIcon = "mdi:broom"
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

const maxAlertsOptions = [
	{ label: "1 Alert", value: 1 },
	{ label: "5 Alert", value: 5 },
	{ label: "10 Alert", value: 10 },
	{ label: "20 Alert", value: 20 }
]

const alertFieldOptions = useStorage<{ label: string; value: string }[]>("alert-fields-history", [], localStorage)

function clearFieldsHistory(field?: string) {
	if (!field) {
		alertFieldOptions.value = []
	} else {
		alertFieldOptions.value = alertFieldOptions.value.filter(o => o.label !== field)
	}
}

function renderFieldTag({ option }: { option: SelectOption; handleClose: () => void }): VNodeChild {
	return h("div", {}, [option.label as string])
}

function renderFieldLabel(option: SelectOption): VNodeChild {
	if (option.type === "group") return option.label + "(Cool!)"
	return [
		h(Icon, {
			style: {
				verticalAlign: "-0.20em",
				marginRight: "4px",
				opacity: 0.6
			},
			name: `carbon:close`,
			onClick(e: Event) {
				e.stopImmediatePropagation()
				e.stopPropagation()
				clearFieldsHistory(option.label?.toString())
			}
		}),
		option.label?.toString()
	]
}

watch(
	() => filters.value.alertField,
	val => {
		if (val) {
			alertFieldOptions.value = _uniqBy(
				[...JSON.parse(JSON.stringify(alertFieldOptions.value)), { label: val, value: val }],
				o => o.label
			)
		}
	}
)

onBeforeMount(() => {
	if (!filters.value.timerange) {
		filters.value.timerange = timerangeOptions[3].value
	}
	if (!filters.value.maxAlerts) {
		filters.value.maxAlerts = maxAlertsOptions[2].value
	}
})
</script>
