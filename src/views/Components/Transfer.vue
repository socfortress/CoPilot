<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Transfer</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/transfer"
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
				<n-transfer
					ref="transfer"
					v-model:value="value1"
					virtual-scroll
					:options="options1"
					source-filterable
					target-filterable
				/>
				<template #code="{ html, js }">
					{{ html(`
					<n-transfer
						ref="transfer"
						v-model:value="value1"
						virtual-scroll
						:options="options1"
						source-filterable
						target-filterable
					/>
					`) }}

					{{
						js(`
						function createOptions() {
							return Array.from({ length: 100 }).map((v, i) => ({
								label: "Option " + i,
								value: i,
								disabled: i % 5 === 0
							}))
						}

						function createValues() {
							return Array.from({ length: 50 }).map((v, i) => i)
						}

						const options1 = createOptions()
						const value1 = ref(createValues())
						
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NTransfer } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

function createOptions() {
	return Array.from({ length: 100 }).map((v, i) => ({
		label: "Option " + i,
		value: i,
		disabled: i % 5 === 0
	}))
}

function createValues() {
	return Array.from({ length: 50 }).map((v, i) => i)
}

const options1 = createOptions()
const value1 = ref(createValues())
</script>
