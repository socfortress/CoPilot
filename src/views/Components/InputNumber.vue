<template>
	<div class="page">
		<div class="page-header">
			<div class="title">InputNumber</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/input-number"
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
				<n-input-number v-model:value="value" clearable />
				<template #code="{ html, js }">
					{{ html(`
					<n-input-number v-model:value="value" clearable />
					`) }}

					{{
						js(`
						const value = ref(0)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Custom parsing">
				<template #description>
					You can use
					<n-text code>parse</n-text>
					and
					<n-text code>format</n-text>
					to custom parsing & display. For example add thousand separator. Usually they should be set
					together, especially you have a custom
					<n-text code>validator</n-text>
					set.
					<br />
					<br />
					Use
					<n-text code>parse</n-text>
					and
					<n-text code>format</n-text>
					will disable
					<n-text code>update-value-on-input</n-text>
					.
				</template>
				<n-space vertical>
					<n-input-number :default-value="1075" :parse="parse" :format="format" />
					<n-input-number :default-value="1075" :parse="parseCurrency" :format="formatCurrency" />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-input-number :default-value="1075" :parse="parse" :format="format" />
						<n-input-number :default-value="1075" :parse="parseCurrency" :format="formatCurrency" />
					</n-space>
					`) }}

					{{
						js(`
						function parse(input: string) {
							const nums = input.replace(/,/g, "").trim()
							if (/^\d+(\.(\d+)?)?$/.test(nums)) return Number(nums)
							return nums === "" ? null : Number.NaN
						}
						function format(value: number | null) {
							if (value === null) return ""
							return value.toLocaleString("en-US")
						}
						function parseCurrency(input: string) {
							const nums = input.replace(/(,|\$|\s)/g, "").trim()
							if (/^\d+(\.(\d+)?)?$/.test(nums)) return Number(nums)
							return nums === "" ? null : Number.NaN
						}
						function formatCurrency(value: number | null) {
							if (value === null) return ""
							return \`\${value.toLocaleString("en-US")} \u{24}\`
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Button placement">
				<template #description>Button can be placed at both ends.</template>
				<n-space vertical>
					<n-input-number v-model:value="value" button-placement="both" />
					<n-input-number v-model:value="value" button-placement="both">
						<template #prefix>$</template>
					</n-input-number>
					<n-input-number v-model:value="value" button-placement="both">
						<template #suffix>฿</template>
					</n-input-number>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-input-number v-model:value="value" button-placement="both" />
						<n-input-number v-model:value="value" button-placement="both">
							<template #prefix>$</template>
						</n-input-number>
						<n-input-number v-model:value="value" button-placement="both">
							<template #suffix>฿</template>
						</n-input-number>
					</n-space>
					`) }}

					{{
						js(`
						const value = ref(0)
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NInputNumber, NText, NSpace } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const value = ref(0)

function parse(input: string) {
	const nums = input.replace(/,/g, "").trim()
	if (/^\d+(\.(\d+)?)?$/.test(nums)) return Number(nums)
	return nums === "" ? null : Number.NaN
}
function format(value: number | null) {
	if (value === null) return ""
	return value.toLocaleString("en-US")
}
function parseCurrency(input: string) {
	const nums = input.replace(/(,|\$|\s)/g, "").trim()
	if (/^\d+(\.(\d+)?)?$/.test(nums)) return Number(nums)
	return nums === "" ? null : Number.NaN
}
function formatCurrency(value: number | null) {
	if (value === null) return ""
	return `${value.toLocaleString("en-US")} \u{24}`
}
</script>
