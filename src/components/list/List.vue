<template>
	<div class="list flex flex-col gap-4">
		<div class="item flex items-center" v-for="item of list" :key="item.name">
			<div class="image flex items-center">
				<img v-if="image" :src="item.image" width="40" height="40" />
				<n-avatar
					v-if="!image"
					:size="40"
					:style="{
						color: item.fgcolor,
						backgroundColor: item.bgcolor
					}"
				>
					{{ item.code }}
				</n-avatar>
			</div>
			<div class="info grow">
				<div class="name">{{ item.name }}</div>
				<div class="adjective" v-if="!hideSubtitle">{{ item.adjective }}</div>
			</div>
			<div class="value flex items-center" :class="item.direction">
				<div class="amount" v-if="!hideValue">{{ item.amount }}</div>
				<Percentage
					v-if="!percentage.hide"
					v-bind="percentage"
					:direction="item.direction"
					:value="item.percentage"
				></Percentage>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, toRefs, computed } from "vue"
import { NAvatar } from "naive-ui"
import { getAirline, getColors, getCompany } from "./data"
import { useThemeStore } from "@/stores/theme"
import Percentage from "@/components/common/Percentage.vue"

interface ListPercentage {
	hide?: boolean
	useColor?: boolean
	useOpacity?: boolean
	useBackground?: boolean
	progress?: "line" | "circle" | false
	icon?: "arrow" | "operator" | false
}
type DataType = "company" | "airline" | "colors"

const props = withDefaults(
	defineProps<{
		dataType?: DataType
		image?: boolean
		hideValue?: boolean
		hideSubtitle?: boolean
		percentage?: ListPercentage
		minWidth?: string
	}>(),
	{
		dataType: "company",
		image: false,
		hideValue: false,
		hideSubtitle: false,
		minWidth: "initial",
		percentage: () => ({
			hide: false,
			useColor: true,
			useBackground: false,
			useOpacity: false,
			icon: "arrow",
			progress: false
		})
	}
)
const { dataType, image, percentage, hideValue, hideSubtitle, minWidth } = toRefs(props)

const secondaryColors = computed(() => Object.values(useThemeStore().secondaryColors))

let data = getCompany(8, {
	palette: secondaryColors.value,
	alphaFG: 1,
	alphaBG: 0.1
})
if (dataType.value === "company") {
	data = getCompany(8, {
		palette: secondaryColors.value,
		alphaFG: 1,
		alphaBG: 0.1
	})
}
if (dataType.value === "airline") {
	data = getAirline(8, {
		palette: secondaryColors.value,
		alphaFG: 1,
		alphaBG: 0.1
	})
}
if (dataType.value === "colors") {
	data = getColors(6)
}

const list = ref(data)
</script>

<style scoped lang="scss">
.list {
	min-width: v-bind(minWidth);
	.item {
		gap: 20px;
		.image {
			img {
				min-width: 40px;
				border-radius: var(--border-radius-small);
			}
			.n-avatar {
				font-size: 12px;
				position: relative;
			}
		}
		.info {
			line-height: 1.25;

			.name {
				font-size: 16px;
			}
			.adjective {
				margin-top: 4px;
				font-size: 14px;
				opacity: 0.6;
			}
		}
		.value {
			font-size: 16px;
			gap: 10px;
			.amount {
				font-weight: 500;
				white-space: nowrap;
			}
		}
	}
}
</style>
