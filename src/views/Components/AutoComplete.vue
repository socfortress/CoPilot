<template>
	<div class="page">
		<div class="page-header">
			<div class="title">AutoComplete</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/auto-complete"
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
				<template #description>Start typing to see how this works.</template>
				<n-auto-complete
					v-model:value="value"
					:input-props="{
						autocomplete: 'disabled'
					}"
					:options="options"
					placeholder="Email"
				/>
				<template #code="{ html, js }">
					{{ html(`
					<n-auto-complete
						v-model:value="value"
						:input-props="{
							autocomplete: 'disabled'
						}"
						:options="options"
						placeholder="Email"
					/>
					`) }}

					{{
						js(`
						const value = ref("")
						const options = computed(() => {
							return ["@gmail.com", "@163.com", "@qq.com"].map(suffix => {
								const prefix = value.value.split("@")[0]
								return {
									label: prefix + suffix,
									value: prefix + suffix
								}
							})
						})
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Whether to show menu">
				<template #description>
					Your can determine is whether to show menu based on value when it is focused.
				</template>
				<n-auto-complete
					v-model:value="value"
					:options="options"
					placeholder="Input 'a' to show menu"
					:get-show="getShow"
				/>
				<template #code="{ html, js }">
					{{ html(`
					<n-auto-complete
						v-model:value="value"
						:options="options"
						placeholder="Input 'a' to show menu"
						:get-show="getShow"
					/>
					`) }}

					{{
						js(`
						const value = ref("")
						const options = computed(() => {
							return ["@gmail.com", "@163.com", "@qq.com"].map(suffix => {
								const prefix = value.value.split("@")[0]
								return {
									label: prefix + suffix,
									value: prefix + suffix
								}
							})
						})
						const getShow = (value: string) => {
							if (value === "a") {
								return true
							}
							return false
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NAutoComplete } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { computed, ref } from "vue"

const value = ref("")
const options = computed(() => {
	return ["@gmail.com", "@163.com", "@qq.com"].map(suffix => {
		const prefix = value.value.split("@")[0]
		return {
			label: prefix + suffix,
			value: prefix + suffix
		}
	})
})
const getShow = (value: string) => {
	if (value === "a") {
		return true
	}
	return false
}
</script>
