<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Dynamic Input</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/dynamic-input"
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
			<CardCodeExample title="Use input preset">
				<template #description>
					By default, the preset element of
					<n-text code>n-dynamic-input</n-text>
					is
					<n-text code>input</n-text>
					.
				</template>
				<div class="mb-3">
					<label>preset:</label>
					<n-select v-model:value="preset" :options="presetOptions" />
				</div>
				<n-dynamic-input
					v-model:value="value"
					placeholder="Please type here"
					:min="3"
					:max="10"
					:preset="preset"
				/>
				<pre>{{ JSON.stringify(value, null, 2) }}</pre>
				<template #code="{ html, js }">
					{{ html(`
					<div class="mb-3">
						<label>preset:</label>
						<n-select v-model:value="preset" :options="presetOptions" />
					</div>
					<n-dynamic-input
						v-model:value="value"
						placeholder="Please type here"
						:min="3"
						:max="10"
						:preset="preset"
					/>
					<pre>\{\{ JSON.stringify(value, null, 2) \}\}</pre>
					`) }}

					{{
						js(`
						const value = ref(["", "", ""])
						const preset = ref<"input" | "pair" | undefined>("input")
						const presetOptions = [
							{
								label: "input",
								value: "input"
							},
							{
								label: "pair",
								value: "pair"
							}
						]

						watch(preset, () => {
							value.value = []
						})
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Customizing input content">
				<n-dynamic-input v-model:value="customValue" :on-create="onCreate" show-sort-button>
					<template #create-button-default>Add whatever you want</template>
					<template #default="{ value }">
						<div style="display: flex; align-items: center; width: 100%">
							<n-checkbox v-model:checked="value.isCheck" style="margin-right: 12px" />
							<n-input-number v-model:value="value.num" style="margin-right: 12px; width: 160px" />
							<n-input v-model:value="value.string" type="text" />
						</div>
					</template>
				</n-dynamic-input>
				<pre>{{ JSON.stringify(customValue, null, 2) }}</pre>

				<template #code="{ html, js }">
					{{ html(`
					<n-dynamic-input v-model:value="customValue" :on-create="onCreate" show-sort-button>
						<template #create-button-default>Add whatever you want</template>
						<template #default="{ value }">
							<div style="display: flex; align-items: center; width: 100%">
								<n-checkbox v-model:checked="value.isCheck" style="margin-right: 12px" />
								<n-input-number v-model:value="value.num" style="margin-right: 12px; width: 160px" />
								<n-input v-model:value="value.string" type="text" />
							</div>
						</template>
					</n-dynamic-input>
					<pre>\{\{ JSON.stringify(customValue, null, 2) \}\}</pre>
					`) }}

					{{
						js(`					
						const customValue = ref([
							{
								isCheck: true,
								num: 1,
								string: "A String"
							}
						])
						function onCreate() {
							return {
								isCheck: false,
								num: 1,
								string: "A String"
							}
						}						
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NDynamicInput, NText, NSelect, NCheckbox, NInputNumber, NInput } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"
import { watch } from "vue"

const value = ref(["", "", ""])
const preset = ref<"input" | "pair" | undefined>("input")
const presetOptions = [
	{
		label: "input",
		value: "input"
	},
	{
		label: "pair",
		value: "pair"
	}
]

const customValue = ref([
	{
		isCheck: true,
		num: 1,
		string: "A String"
	}
])
function onCreate() {
	return {
		isCheck: false,
		num: 1,
		string: "A String"
	}
}

watch(preset, () => {
	value.value = []
})
</script>
