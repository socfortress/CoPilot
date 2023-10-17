<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Date Picker</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/date-picker"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<div class="mb-3">
					<label>type:</label>
					<n-select v-model:value="type" :options="typeOptions" />
				</div>
				<n-date-picker v-model:value="timestamp" :type="type" clearable />
				<template #code="{ html, js }">
					{{ html(`
					<div class="mb-3">
						<label>type:</label>
						<n-select v-model:value="type" :options="typeOptions" />
					</div>
					<n-date-picker v-model:value="timestamp" :type="type" clearable />
					`) }}

					{{
						js(`
						type Value = number | [number, number] | null

						const timestamp = ref\<\V\a\lu\e\>(new Date().getTime())
						const type = ref\<\DatePickerType\>\("date")
						const typeOptions = [
							{
								label: "Date",
								value: "date"
							},
							{
								label: "Date time",
								value: "datetime"
							},
							{
								label: "Date range",
								value: "daterange"
							},
							{
								label: "Date time range",
								value: "datetimerange"
							},
							{
								label: "Month",
								value: "month"
							},
							{
								label: "Month range",
								value: "monthrange"
							},
							{
								label: "Year",
								value: "year"
							},
							{
								label: "Year range",
								value: "yearrange"
							},
							{
								label: "Quarter",
								value: "quarter"
							},
							{
								label: "Quarter range",
								value: "quarterrange"
							}
						]

						watch(type, () => {
							timestamp.value = null
						})
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Disabled specific time">
				<n-date-picker type="date" :default-value="Date.now()" :is-date-disabled="dateDisabled" />
				<template #code="{ html, js }">
					{{ html(`
					<div>
						<n-date-picker type="date" :default-value="Date.now()" :is-date-disabled="dateDisabled" />
					</div>
					`) }}

					{{
						js(`
						function dateDisabled(ts: number) {
							const date = new Date(ts).getDate()
							return date < 15
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Shortcuts">
				<template #description>You can customize some shorcut buttons.</template>
				<n-date-picker v-model:value="ts1" type="date" :shortcuts="shortcuts" />
				<template #code="{ html, js }">
					{{ html(`
					<div>
						<n-date-picker v-model:value="ts1" type="date" :shortcuts="shortcuts" />
					</div>
					`) }}

					{{
						js(`
						const ts1 = ref(null)
						const shortcuts = {
							"Honey birthday": 1631203200000,
							Yesterday: () => new Date().getTime() - 24 * 60 * 60 * 1000
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Format">
				<n-date-picker v-model:value="timestamp" type="datetime" clearable :format="format" />
				<template #code="{ html, js }">
					{{ html(`
					<div>
						<n-date-picker v-model:value="timestamp" type="datetime" clearable :format="format" />
					</div>
					`) }}

					{{
						js(`
						const format = "yyyy/MM/dd - HH:mm"
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Use panel only">
				<n-date-picker panel type="date" class="!mx-auto" />
				<template #code="{ html }">
					{{ html(`
					<div>
						<n-date-picker panel type="date" />
					</div>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NDatePicker, NSelect } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref, watch } from "vue"
import { type DatePickerType } from "naive-ui/es/date-picker/src/config"

type Value = number | [number, number] | null

const timestamp = ref<Value>(new Date().getTime())
const type = ref<DatePickerType>("date")
const typeOptions = [
	{
		label: "Date",
		value: "date"
	},
	{
		label: "Date time",
		value: "datetime"
	},
	{
		label: "Date range",
		value: "daterange"
	},
	{
		label: "Date time range",
		value: "datetimerange"
	},
	{
		label: "Month",
		value: "month"
	},
	{
		label: "Month range",
		value: "monthrange"
	},
	{
		label: "Year",
		value: "year"
	},
	{
		label: "Year range",
		value: "yearrange"
	},
	{
		label: "Quarter",
		value: "quarter"
	},
	{
		label: "Quarter range",
		value: "quarterrange"
	}
]

function dateDisabled(ts: number) {
	const date = new Date(ts).getDate()
	return date < 15
}

watch(type, () => {
	timestamp.value = null
})

const ts1 = ref(null)
const shortcuts = {
	"Honey birthday": 1631203200000,
	Yesterday: () => new Date().getTime() - 24 * 60 * 60 * 1000
}

const format = "yyyy/MM/dd - HH:mm"
</script>
