<template>
	<n-card :bordered="cardWrap" :content-style="contentStyle" :style="contentStyle">
		<div class="card-wrap flex gap-4" :class="{ 'flex-col': vertical }">
			<div class="icon-box" v-if="$slots.icon">
				<div class="icon">
					<slot name="icon"></slot>
				</div>
			</div>
			<div class="info flex flex-col grow">
				<div class="header flex items-center justify-between gap-2">
					<div class="title grow">
						{{ title || randomTitle }}
					</div>
					<Percentage v-if="percentage && percentageProps" v-bind="percentageProps"></Percentage>
				</div>
				<div class="value">{{ valueString }}</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard } from "naive-ui"
import { toRefs, computed, ref } from "vue"
import Percentage, { type PercentageProps } from "@/components/common/Percentage.vue"

const props = defineProps<{
	title: string
	val?: number
	valString?: string
	currency?: string
	cardWrap?: boolean
	vertical?: boolean
	percentage?: boolean
	percentageProps?: PercentageProps
}>()
const { title, val, valString, currency, percentage, percentageProps, cardWrap, vertical } = toRefs(props)

const randomTitle = ref(faker.commerce.department())

const contentStyle = computed(() => (cardWrap.value ? "" : "padding:0;background-color:transparent"))

const valueString = computed(() => {
	if (valString?.value) {
		return valString.value
	}

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
.card-wrap {
	height: 100%;
	width: 100%;
	overflow: hidden;

	.info {
		overflow: hidden;
		.header {
			overflow: hidden;
			margin-bottom: 6px;
			white-space: nowrap;

			.title {
				text-overflow: ellipsis;
				white-space: nowrap;
				overflow: hidden;
			}
		}
		.value {
			font-family: var(--font-family-display);
			font-size: 26px;
			font-weight: bold;
			text-overflow: ellipsis;
			white-space: nowrap;
			overflow: hidden;
		}
	}
}
</style>
