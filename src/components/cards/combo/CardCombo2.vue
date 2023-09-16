<template>
	<n-card>
		<div class="flex items-center h-full">
			<div
				class="card-wrap flex gap-4"
				:class="{ 'items-center': centered, 'text-center': centered, 'flex-col': !horizontal }"
			>
				<div class="icon">
					<slot name="icon"></slot>
				</div>
				<div class="info flex flex-col">
					<div class="value">{{ valueString }}</div>
					<div class="title">{{ title }}</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard } from "naive-ui"
import { toRefs, computed } from "vue"

const props = defineProps<{
	title: string
	val?: number
	currency?: string
	centered?: boolean
	horizontal?: boolean
}>()
const { title, val, currency, centered, horizontal } = toRefs(props)

const valueString = computed(() => {
	const value = val?.value || faker.number.int({ min: 1000, max: 5000 })

	if (!value) return ""

	if (currency?.value) {
		return new Intl.NumberFormat("en-EN", { style: "currency", currency: "USD" }).format(value)
	} else {
		return new Intl.NumberFormat("en-EN").format(value)
	}
})
</script>

<style scoped lang="scss">
.n-card {
	.card-wrap {
		width: 100%;

		.title {
			font-size: 18px;
			word-break: initial;
		}
		.value {
			font-family: var(--font-family-display);
			font-size: 22px;
			font-weight: bold;
			margin-bottom: 6px;
		}
	}
}
</style>
