<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Select</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/select"
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
				<n-space vertical>
					<n-select v-model:value="value" :options="options" />
					<n-select v-model:value="value" disabled :options="options" />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-select v-model:value="value" :options="options" />
						<n-select v-model:value="value" disabled :options="options" />
					</n-space>
					`) }}

					{{
						js(`
						const value = ref(null)
						const options = [
							{
								label: "Everybody's Got Something to Hide Except Me and My Monkey",
								value: "song0",
								disabled: true
							},
							{
								label: "Drive My Car",
								value: "song1"
							},
							{
								label: "Norwegian Wood",
								value: "song2"
							},
							{
								label: "You Won't See",
								value: "song3",
								disabled: true
							},
							{
								label: "Nowhere Man",
								value: "song4"
							},
							{
								label: "Think For Yourself",
								value: "song5"
							},
							{
								label: "The Word",
								value: "song6"
							},
							{
								label: "Michelle",
								value: "song7",
								disabled: true
							},
							{
								label: "What goes on",
								value: "song8"
							},
							{
								label: "Girl",
								value: "song9"
							},
							{
								label: "I'm looking through you",
								value: "song10"
							},
							{
								label: "In My Life",
								value: "song11"
							},
							{
								label: "Wait",
								value: "song12"
							}
						]
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Multiple & Create">
				<n-select v-model:value="multipleSelectValue" filterable multiple tag :options="options" clearable />
				<template #code="{ html, js }">
					{{ html(`
					<n-select
						v-model:value="multipleSelectValue"
						filterable
						multiple
						tag
						:options="options"
						clearable
					/>
					`) }}

					{{
						js(`
						const multipleSelectValue = ref(null)
						const options = [
							{
								label: "Everybody's Got Something to Hide Except Me and My Monkey",
								value: "song0",
								disabled: true
							},
							{
								label: "Drive My Car",
								value: "song1"
							},
							{
								label: "Norwegian Wood",
								value: "song2"
							},
							{
								label: "You Won't See",
								value: "song3",
								disabled: true
							},
							{
								label: "Nowhere Man",
								value: "song4"
							},
							{
								label: "Think For Yourself",
								value: "song5"
							},
							{
								label: "The Word",
								value: "song6"
							},
							{
								label: "Michelle",
								value: "song7",
								disabled: true
							},
							{
								label: "What goes on",
								value: "song8"
							},
							{
								label: "Girl",
								value: "song9"
							},
							{
								label: "I'm looking through you",
								value: "song10"
							},
							{
								label: "In My Life",
								value: "song11"
							},
							{
								label: "Wait",
								value: "song12"
							}
						]
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NSelect } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const value = ref(null)
const multipleSelectValue = ref(null)
const options = [
	{
		label: "Everybody's Got Something to Hide Except Me and My Monkey",
		value: "song0",
		disabled: true
	},
	{
		label: "Drive My Car",
		value: "song1"
	},
	{
		label: "Norwegian Wood",
		value: "song2"
	},
	{
		label: "You Won't See",
		value: "song3",
		disabled: true
	},
	{
		label: "Nowhere Man",
		value: "song4"
	},
	{
		label: "Think For Yourself",
		value: "song5"
	},
	{
		label: "The Word",
		value: "song6"
	},
	{
		label: "Michelle",
		value: "song7",
		disabled: true
	},
	{
		label: "What goes on",
		value: "song8"
	},
	{
		label: "Girl",
		value: "song9"
	},
	{
		label: "I'm looking through you",
		value: "song10"
	},
	{
		label: "In My Life",
		value: "song11"
	},
	{
		label: "Wait",
		value: "song12"
	}
]
</script>
