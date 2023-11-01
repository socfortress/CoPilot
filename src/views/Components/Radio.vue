<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Radio</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/radio"
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
				<n-space>
					<n-radio
						:checked="checkedValue === 'Definitely Maybe'"
						value="Definitely Maybe"
						name="basic-demo"
						@change="handleChange"
					>
						Definitely Maybe
					</n-radio>
					<n-radio
						:checked="checkedValue === 'Be Here Now'"
						value="Be Here Now"
						name="basic-demo"
						@change="handleChange"
					>
						Be Here Now
					</n-radio>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-radio
							:checked="checkedValue === 'Definitely Maybe'"
							value="Definitely Maybe"
							name="basic-demo"
							@change="handleChange"
						>
							Definitely Maybe
						</n-radio>
						<n-radio
							:checked="checkedValue === 'Be Here Now'"
							value="Be Here Now"
							name="basic-demo"
							@change="handleChange"
						>
							Be Here Now
						</n-radio>
					</n-space>
					`) }}

					{{
						js(`
						const checkedValue = ref\<\string | null\>\(null)

						function handleChange(e: Event) {
							checkedValue.value = (e.target as HTMLInputElement).value
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Button group">
				<template #description>Sometimes a radio button group can look more elegant.</template>
				<n-space vertical>
					<n-radio-group v-model:value="value" name="radiobuttongroup">
						<n-radio-button
							v-for="song in songs"
							:key="song.value"
							:value="song.value"
							:label="song.label"
						/>
					</n-radio-group>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-radio-group v-model:value="value" name="radiobuttongroup">
							<n-radio-button
								v-for="song in songs"
								:key="song.value"
								:value="song.value"
								:label="song.label"
							/>
						</n-radio-group>
					</n-space>
					`) }}

					{{
						js(`
						const value = ref(null)

						const songs = [
							{
								value: "Rock'n'Roll Star",
								label: "Rock'n'Roll Star"
							},
							{
								value: "Shakermaker",
								label: "Shakermaker"
							},
							{
								value: "Live Forever",
								label: "Live Forever"
							},
							{
								value: "Up in the Sky",
								label: "Up in the Sky"
							},
							{
								value: "...",
								label: "..."
							}
						].map(s => {
							s.value = s.value.toLowerCase()
							return s
						})
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NRadio, NRadioGroup, NRadioButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const checkedValue = ref<string | null>(null)

function handleChange(e: Event) {
	checkedValue.value = (e.target as HTMLInputElement).value
}

const value = ref(null)

const songs = [
	{
		value: "Rock'n'Roll Star",
		label: "Rock'n'Roll Star"
	},
	{
		value: "Shakermaker",
		label: "Shakermaker"
	},
	{
		value: "Live Forever",
		label: "Live Forever"
	},
	{
		value: "Up in the Sky",
		label: "Up in the Sky"
	},
	{
		value: "...",
		label: "..."
	}
].map(s => {
	s.value = s.value.toLowerCase()
	return s
})
</script>
