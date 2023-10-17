<template>
	<div class="page">
		<div class="main-grid gap-5">
			<div class="box-card-1">
				<CardCombo1 title="Sales" class="h-full">
					<template #icon>
						<CardComboIcon :iconName="SalesIcon" boxed></CardComboIcon>
					</template>
				</CardCombo1>
			</div>
			<div class="box-card-2">
				<CardCombo6
					cardWrap
					title="Category overview"
					:segmented="{
						content: true
					}"
				/>
			</div>
			<div class="box-card-3">
				<CardCombo1 title="Orders" class="h-full">
					<template #icon>
						<CardComboIcon :iconName="OrdersIcon" boxed></CardComboIcon>
					</template>
				</CardCombo1>
			</div>

			<div class="left-col">
				<div class="flex flex-col gap-5 h-full">
					<div class="flex">
						<CardCombo8 />
					</div>
					<div class="flex grow">
						<CardActions
							:segmented="{
								action: false
							}"
							:hideSubtitle="true"
							showImage
							hideMenu
							:hoverable="false"
							actionBoxTransparent
							title="Best product"
							image="/images/headphones.jpg"
							class="h-full"
						>
							<template #default>
								<DemoList
									:hide-value="false"
									data-type="colors"
									:percentage="{ progress: 'circle', icon: 'operator', useColor: true }"
								/>
							</template>
							<template #action>
								<DemoChart
									type="area"
									data-type="week"
									hideXaxisLabels
									:strokeWidth="2"
									:fontColor="textSecondaryColor"
								/>
							</template>
						</CardActions>
					</div>
				</div>
			</div>

			<div class="right-col">
				<div class="flex flex-col gap-5 h-full">
					<!-- three cards -->
					<div class="flex gap-5 w-full" :class="{ 'flex-col': isCardHorizontal }" ref="cardsContainer">
						<CardCombo2 title="Completed" centered :horizontal="isCardHorizontal" class="basis-1/3">
							<template #icon>
								<CardComboIcon
									:iconName="CompletedIcon"
									boxed
									:boxSize="50"
									:color="style['--primary-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Pending" centered :horizontal="isCardHorizontal" class="basis-1/3">
							<template #icon>
								<CardComboIcon
									:iconName="PendingIcon"
									boxed
									:boxSize="50"
									:color="style['--secondary3-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Shipped" centered :horizontal="isCardHorizontal" class="basis-1/3">
							<template #icon>
								<CardComboIcon
									:iconName="ShippedIcon"
									boxed
									:boxSize="50"
									:color="style['--secondary1-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
					</div>

					<div class="flex gap-5 w-full grow" :class="{ 'flex-col': isRightColHorizontal }">
						<div class="flex flex-col gap-5 h-full" :class="{ 'basis-1/2': !isSwitchChartHorizontal }">
							<div class="grow">
								<CardCombo1
									title="Revenue"
									class="h-full !text-white"
									type="bar"
									:style="`background-color: ${style['--secondary3-color']}`"
									:dataCount="10"
									:chartPaddingTop="
										isRightColHorizontal && !isSwitchChartHorizontal ? '0px' : '100px'
									"
									currency="USD"
									chartBarGradient
									:chartHeight="isRightColHorizontal && !isSwitchChartHorizontal ? 40 : 200"
									chartColor="#ffffff"
								>
									<template #icon>
										<CardComboIcon :iconName="RevenueIcon" boxed color="white"></CardComboIcon>
									</template>
								</CardCombo1>
							</div>
							<CardCombo3 class="h-full" oneSeries></CardCombo3>
						</div>
						<div class="flex flex-col gap-5 h-full basis-1/2" v-if="!isSwitchChartHorizontal">
							<CardCombo5 size="large" class="h-full" />
						</div>
					</div>
				</div>
			</div>

			<div class="box-bottom">
				<div class="flex flex-col gap-5">
					<CardCombo5 size="large" v-if="isSwitchChartHorizontal" />
					<CardWrapper v-slot="{ expand, isExpand, reload }" class="h-full w-full">
						<CardExtra6
							class="h-full"
							:expand="expand"
							:isExpand="isExpand"
							:reload="reload"
							showActions
							showDate
							:minWidth="760"
						/>
					</CardWrapper>
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import DemoChart from "@/components/charts/DemoApex.vue"
import DemoList from "@/components/list/List.vue"
import { useWindowSize, useElementSize } from "@vueuse/core"
import { computed, ref } from "vue"
import { useThemeStore } from "@/stores/theme"

const CompletedIcon = "carbon:checkmark-outline"
const PendingIcon = "carbon:hourglass"
const ShippedIcon = "carbon:send"
const SalesIcon = "carbon:wireless-checkout"
const OrdersIcon = "carbon:shopping-cart"
const RevenueIcon = "carbon:money"

const { width } = useWindowSize()
const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
const textSecondaryColor = computed<string>(() => style.value["--fg-secondary-color"])
const cardsContainer = ref(null)
const { width: widthCardsContainer } = useElementSize(cardsContainer)
const isCardHorizontal = computed(() => widthCardsContainer.value < 460)
const isRightColHorizontal = computed(() => width.value < 1400)
const isSwitchChartHorizontal = computed(() => width.value < 1310)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/common.scss";

.page {
	.main-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		grid-template-rows: repeat(1, minmax(0, 1fr));

		grid-template-areas:
			"box1 box2 box3 box3"
			"boxleft boxleft boxright boxright"
			"boxbottom boxbottom boxbottom boxbottom";

		@media (max-width: 1400px) {
			grid-template-areas:
				"box1 box1 box2 box2"
				"box3 box3 box3 box3"
				"boxleft boxleft boxright boxright"
				"boxbottom boxbottom boxbottom boxbottom";
		}
		@media (max-width: 1000px) {
			grid-template-areas:
				"box1 box1 box2 box2"
				"box3 box3 box3 box3"
				"boxleft boxleft boxleft boxleft"
				"boxright boxright boxright boxright"
				"boxbottom boxbottom boxbottom boxbottom";
		}
		@media (max-width: 560px) {
			grid-template-areas:
				"box1 box1 box1 box1"
				"box2 box2 box2 box2"
				"box3 box3 box3 box3"
				"boxleft boxleft boxleft boxleft"
				"boxright boxright boxright boxright"
				"boxbottom boxbottom boxbottom boxbottom";
		}
	}

	.box-card-1 {
		grid-area: box1;
	}
	.box-card-2 {
		grid-area: box2;
	}
	.box-card-3 {
		grid-area: box3;
	}
	.box-bottom {
		grid-area: boxbottom;
	}
	.left-col {
		grid-area: boxleft;
	}
	.right-col {
		grid-area: boxright;
	}
}
</style>
