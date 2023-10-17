<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Popselect</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/popselect"
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
				<n-popselect v-model:value="value" :options="options">
					<n-button>{{ value || "Popselect" }}</n-button>
				</n-popselect>
				<template #code="{ html, js }">
					{{ html(`
					<n-popselect v-model:value="value" :options="options">
						<n-button>\{\{ value || "Popselect" \}\}</n-button>
					</n-popselect>
					`) }}

					{{
						js(`
						const value = ref("Drive My Car")
						const options = [
							{
								label: "Drive My Car",
								value: "Drive My Car"
							},
							{
								label: "Norwegian Wood",
								value: "Norwegian Wood"
							},
							{
								label: "You Won't See",
								value: "You Won't See",
								disabled: true
							},
							{
								label: "Nowhere Man",
								value: "Nowhere Man"
							},
							{
								label: "Think For Yourself",
								value: "Think For Yourself"
							},
							{
								label: "The Word",
								value: "The Word"
							},
							{
								label: "Michelle",
								value: "Michelle",
								disabled: true
							},
							{
								label: "What goes on",
								value: "What goes on"
							},
							{
								label: "Girl",
								value: "Girl"
							},
							{
								label: "I'm looking through you",
								value: "I'm looking through you"
							},
							{
								label: "In My Life",
								value: "In My Life"
							},
							{
								label: "Wait",
								value: "Wait"
							}
						]
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Multiple">
				<n-popselect v-model:value="value1" :options="options" multiple scrollable>
					<n-button>{{ Array.isArray(value1) && value1.length ? value1 : "Nothing" }}</n-button>
				</n-popselect>
				<template #code="{ html, js }">
					{{ html(`
					<n-popselect v-model:value="value1" :options="options" multiple scrollable>
						<n-button>\{\{ Array.isArray(value1) && value1.length ? value1 : "Nothing" \}\}</n-button>
					</n-popselect>
					`) }}

					{{
						js(`
							const value1 = ref\<\string[] | null\>\(null)
							const options = [
								{
									label: "Drive My Car",
									value: "Drive My Car"
								},
								{
									label: "Norwegian Wood",
									value: "Norwegian Wood"
								},
								{
									label: "You Won't See",
									value: "You Won't See",
									disabled: true
								},
								{
									label: "Nowhere Man",
									value: "Nowhere Man"
								},
								{
									label: "Think For Yourself",
									value: "Think For Yourself"
								},
								{
									label: "The Word",
									value: "The Word"
								},
								{
									label: "Michelle",
									value: "Michelle",
									disabled: true
								},
								{
									label: "What goes on",
									value: "What goes on"
								},
								{
									label: "Girl",
									value: "Girl"
								},
								{
									label: "I'm looking through you",
									value: "I'm looking through you"
								},
								{
									label: "In My Life",
									value: "In My Life"
								},
								{
									label: "Wait",
									value: "Wait"
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
import { NPopselect, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const value = ref("Drive My Car")
const value1 = ref<string[] | null>(null)
const options = [
	{
		label: "Drive My Car",
		value: "Drive My Car"
	},
	{
		label: "Norwegian Wood",
		value: "Norwegian Wood"
	},
	{
		label: "You Won't See",
		value: "You Won't See",
		disabled: true
	},
	{
		label: "Nowhere Man",
		value: "Nowhere Man"
	},
	{
		label: "Think For Yourself",
		value: "Think For Yourself"
	},
	{
		label: "The Word",
		value: "The Word"
	},
	{
		label: "Michelle",
		value: "Michelle",
		disabled: true
	},
	{
		label: "What goes on",
		value: "What goes on"
	},
	{
		label: "Girl",
		value: "Girl"
	},
	{
		label: "I'm looking through you",
		value: "I'm looking through you"
	},
	{
		label: "In My Life",
		value: "In My Life"
	},
	{
		label: "Wait",
		value: "Wait"
	}
]
</script>
