<template>
	<div class="page">
		<div class="page-header">
			<div class="title">TreeSelect</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/tree-select"
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
				<n-tree-select :options="options" default-value="Drive My Car" @update:value="handleUpdateValue" />
				<template #code="{ html, js }">
					{{ html(`
					<n-tree-select :options="options" default-value="Drive My Car" @update:value="handleUpdateValue" />
					`) }}

					{{
						js(`
						function handleUpdateValue(
							value: string | number | Array\<\string | number\>\ | null,
							option: TreeSelectOption | null | Array\<\TreeSelectOption | null\>\
						) {
							console.log(value, option)
						}
						const options = [
							{
								label: "Rubber Soul",
								key: "Rubber Soul",
								children: [
									{
										label: "Everybody's Got Something to Hide Except Me and My Monkey",
										key: "Everybody's Got Something to Hide Except Me and My Monkey"
									},
									{
										label: "Drive My Car",
										key: "Drive My Car",
										disabled: true
									},
									{
										label: "Norwegian Wood",
										key: "Norwegian Wood"
									},
									{
										label: "You Won't See",
										key: "You Won't See",
										disabled: true
									},
									{
										label: "Nowhere Man",
										key: "Nowhere Man"
									},
									{
										label: "Think For Yourself",
										key: "Think For Yourself"
									},
									{
										label: "The Word",
										key: "The Word"
									},
									{
										label: "Michelle",
										key: "Michelle",
										disabled: true
									},
									{
										label: "What goes on",
										key: "What goes on"
									},
									{
										label: "Girl",
										key: "Girl"
									},
									{
										label: "I'm looking through you",
										key: "I'm looking through you"
									},
									{
										label: "In My Life",
										key: "In My Life"
									},
									{
										label: "Wait",
										key: "Wait"
									}
								]
							},
							{
								label: "Let It Be",
								key: "Let It Be Album",
								children: [
									{
										label: "Two Of Us",
										key: "Two Of Us"
									},
									{
										label: "Dig A Pony",
										key: "Dig A Pony"
									},
									{
										label: "Across The Universe",
										key: "Across The Universe"
									},
									{
										label: "I Me Mine",
										key: "I Me Mine"
									},
									{
										label: "Dig It",
										key: "Dig It"
									},
									{
										label: "Let It Be",
										key: "Let It Be"
									},
									{
										label: "Maggie Mae",
										key: "Maggie Mae"
									},
									{
										label: "I've Got A Feeling",
										key: "I've Got A Feeling"
									},
									{
										label: "One After 909",
										key: "One After 909"
									},
									{
										label: "The Long And Winding Road",
										key: "The Long And Winding Road"
									},
									{
										label: "For You Blue",
										key: "For You Blue"
									},
									{
										label: "Get Back",
										key: "Get Back"
									}
								]
							}
						]
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Use checkbox">
				<n-tree-select
					multiple
					cascade
					clearable
					checkable
					filterable
					:options="options"
					:default-value="['Norwegian Wood']"
				/>
				<template #code="{ html, js }">
					{{ html(`
					<n-tree-select
						multiple
						clearable
						cascade
						checkable
						filterable
						:options="options"
						:default-value="['Norwegian Wood']"
					/>
					`) }}

					{{
						js(`
						function handleUpdateValue(
							value: string | number | Array\<\string | number\>\ | null,
							option: TreeSelectOption | null | Array\<\TreeSelectOption | null\>\
						) {
							console.log(value, option)
						}
						const options = [
							{
								label: "Rubber Soul",
								key: "Rubber Soul",
								children: [
									{
										label: "Everybody's Got Something to Hide Except Me and My Monkey",
										key: "Everybody's Got Something to Hide Except Me and My Monkey"
									},
									{
										label: "Drive My Car",
										key: "Drive My Car",
										disabled: true
									},
									{
										label: "Norwegian Wood",
										key: "Norwegian Wood"
									},
									{
										label: "You Won't See",
										key: "You Won't See",
										disabled: true
									},
									{
										label: "Nowhere Man",
										key: "Nowhere Man"
									},
									{
										label: "Think For Yourself",
										key: "Think For Yourself"
									},
									{
										label: "The Word",
										key: "The Word"
									},
									{
										label: "Michelle",
										key: "Michelle",
										disabled: true
									},
									{
										label: "What goes on",
										key: "What goes on"
									},
									{
										label: "Girl",
										key: "Girl"
									},
									{
										label: "I'm looking through you",
										key: "I'm looking through you"
									},
									{
										label: "In My Life",
										key: "In My Life"
									},
									{
										label: "Wait",
										key: "Wait"
									}
								]
							},
							{
								label: "Let It Be",
								key: "Let It Be Album",
								children: [
									{
										label: "Two Of Us",
										key: "Two Of Us"
									},
									{
										label: "Dig A Pony",
										key: "Dig A Pony"
									},
									{
										label: "Across The Universe",
										key: "Across The Universe"
									},
									{
										label: "I Me Mine",
										key: "I Me Mine"
									},
									{
										label: "Dig It",
										key: "Dig It"
									},
									{
										label: "Let It Be",
										key: "Let It Be"
									},
									{
										label: "Maggie Mae",
										key: "Maggie Mae"
									},
									{
										label: "I've Got A Feeling",
										key: "I've Got A Feeling"
									},
									{
										label: "One After 909",
										key: "One After 909"
									},
									{
										label: "The Long And Winding Road",
										key: "The Long And Winding Road"
									},
									{
										label: "For You Blue",
										key: "For You Blue"
									},
									{
										label: "Get Back",
										key: "Get Back"
									}
								]
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
import { type TreeSelectOption, NTreeSelect } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

function handleUpdateValue(
	value: string | number | Array<string | number> | null,
	option: TreeSelectOption | null | Array<TreeSelectOption | null>
) {
	console.log(value, option)
}
const options = [
	{
		label: "Rubber Soul",
		key: "Rubber Soul",
		children: [
			{
				label: "Everybody's Got Something to Hide Except Me and My Monkey",
				key: "Everybody's Got Something to Hide Except Me and My Monkey"
			},
			{
				label: "Drive My Car",
				key: "Drive My Car",
				disabled: true
			},
			{
				label: "Norwegian Wood",
				key: "Norwegian Wood"
			},
			{
				label: "You Won't See",
				key: "You Won't See",
				disabled: true
			},
			{
				label: "Nowhere Man",
				key: "Nowhere Man"
			},
			{
				label: "Think For Yourself",
				key: "Think For Yourself"
			},
			{
				label: "The Word",
				key: "The Word"
			},
			{
				label: "Michelle",
				key: "Michelle",
				disabled: true
			},
			{
				label: "What goes on",
				key: "What goes on"
			},
			{
				label: "Girl",
				key: "Girl"
			},
			{
				label: "I'm looking through you",
				key: "I'm looking through you"
			},
			{
				label: "In My Life",
				key: "In My Life"
			},
			{
				label: "Wait",
				key: "Wait"
			}
		]
	},
	{
		label: "Let It Be",
		key: "Let It Be Album",
		children: [
			{
				label: "Two Of Us",
				key: "Two Of Us"
			},
			{
				label: "Dig A Pony",
				key: "Dig A Pony"
			},
			{
				label: "Across The Universe",
				key: "Across The Universe"
			},
			{
				label: "I Me Mine",
				key: "I Me Mine"
			},
			{
				label: "Dig It",
				key: "Dig It"
			},
			{
				label: "Let It Be",
				key: "Let It Be"
			},
			{
				label: "Maggie Mae",
				key: "Maggie Mae"
			},
			{
				label: "I've Got A Feeling",
				key: "I've Got A Feeling"
			},
			{
				label: "One After 909",
				key: "One After 909"
			},
			{
				label: "The Long And Winding Road",
				key: "The Long And Winding Road"
			},
			{
				label: "For You Blue",
				key: "For You Blue"
			},
			{
				label: "Get Back",
				key: "Get Back"
			}
		]
	}
]
</script>
