<template>
	<n-card :bordered="cardWrap" :content-style="contentStyle" :style="contentStyle">
		<div class="card-wrap flex flex-col gap-6">
			<div class="header flex items-center gap-3" v-if="!hideHeader">
				<div class="icon-box" v-if="$slots.icon">
					<div class="icon">
						<slot name="icon"></slot>
					</div>
				</div>
				<div class="title grow truncate">
					{{ title || randomTitle }}
				</div>
				<div class="per-box" v-if="showPercentage">
					<Percentage :value="percentage" useColor :direction="percentageDirection" />
				</div>
			</div>
			<div class="progress flex flex-col gap-2">
				<div class="component">
					<n-progress
						type="line"
						:status="percentageDirection === 'up' ? 'success' : 'error'"
						:percentage="progress"
						:show-indicator="false"
						:height="6"
						:border-radius="0"
					/>
				</div>
				<div class="info flex justify-between" v-if="!hideInfo">
					<div class="text">{{ value }} • {{ text }}</div>
					<div class="value">{{ progress }}%</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NProgress } from "naive-ui"
import Percentage, { type PercentageProps } from "@/components/common/Percentage.vue"
import { toRefs, computed, ref } from "vue"

const props = defineProps<{
	title?: string
	cardWrap?: boolean
	showPercentage?: boolean
	hideHeader?: boolean
	hideInfo?: boolean
}>()
const { title, showPercentage, cardWrap, hideHeader, hideInfo } = toRefs(props)

const randomTitle = ref(faker.company.name())
const text = ref(faker.commerce.product())

const percentageDirection = ref<PercentageProps["direction"]>(faker.datatype.boolean() ? "up" : "down")
const percentage = ref(faker.number.int({ min: 10, max: 90 }))
const progress = ref(faker.number.int({ min: 10, max: 90 }))

const value = ref(new Intl.NumberFormat("en-EN", {}).format(faker.number.int({ min: 1000, max: 9000 })))

const contentStyle = computed(() => (cardWrap.value ? "" : "padding:0;background-color:transparent"))
</script>

<style scoped lang="scss">
.card-wrap {
	height: 100%;
	width: 100%;

	.header {
		.title {
			font-family: var(--font-family-display);
			font-size: 18px;
			font-weight: 600;
			letter-spacing: -0.025em;
		}
	}

	.progress {
		.info {
			color: var(--fg-secondary-color);
			font-family: var(--font-family);
			font-size: 14px;
		}
	}
}
</style>
