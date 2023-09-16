<template>
	<div class="page">
		<div class="main-grid gap-5">
			<!-- main col -->
			<div class="main-col">
				<div class="flex flex-col gap-5 h-full">
					<!-- big chart -->
					<div class="flex main-chart-wrap">
						<CardCombo3 class="h-full"></CardCombo3>
					</div>

					<!-- four cards -->
					<div class="gap-5 four-cards-wrap">
						<CardCombo4
							title="Users"
							valString="248.3K"
							percentage
							cardWrap
							iconBox
							:percentageProps="{
								value: 2.45,
								direction: 'up'
							}"
						>
							<template #icon>
								<CardComboIcon boxed>
									<UsersIcon />
								</CardComboIcon>
							</template>
						</CardCombo4>
						<CardCombo4
							title="Page Views"
							valString="486.9K"
							percentage
							cardWrap
							:percentageProps="{
								value: 1.88,
								direction: 'down'
							}"
						>
							<template #icon>
								<CardComboIcon boxed>
									<ViewsIcon />
								</CardComboIcon>
							</template>
						</CardCombo4>
						<CardCombo4
							title="Active Users"
							valString="73.8K"
							percentage
							cardWrap
							:percentageProps="{
								value: 3.24,
								direction: 'up'
							}"
						>
							<template #icon>
								<CardComboIcon boxed>
									<ActivityIcon />
								</CardComboIcon>
							</template>
						</CardCombo4>
						<CardCombo4
							title="Uploads"
							valString="42.1K"
							percentage
							cardWrap
							:percentageProps="{
								value: 0.43,
								direction: 'down'
							}"
						>
							<template #icon>
								<CardComboIcon boxed>
									<UploadsIcon />
								</CardComboIcon>
							</template>
						</CardCombo4>
					</div>

					<!-- list -->
					<div class="flex grow">
						<CardWrapper v-slot="{ expand, isExpand, reload }" class="h-full grow w-full">
							<CardActions
								:expand="expand"
								:isExpand="isExpand"
								:reload="reload"
								class="h-full"
								title="Leading Companies"
								:segmented="{
									content: true,
									footer: true
								}"
							>
								<template #default>
									<DemoList class="my-4" minWidth="400px" />
								</template>
								<template #footer>
									<DemoChart
										type="bar"
										data-type="months"
										:highlight="true"
										class="mt-4"
										:fontColor="textSecondaryColor"
									/>
								</template>
							</CardActions>
						</CardWrapper>
					</div>
				</div>
			</div>

			<!-- side col -->
			<div class="side-col">
				<div class="flex flex-col gap-5 h-full">
					<!-- tiny chart -->
					<div class="flex">
						<CardCombo1
							title="Sessions"
							class="h-full !text-white"
							:style="`background-color: ${chartBg}`"
							chartColor="#ffffff"
						>
							<template #icon>
								<CardComboIcon boxed color="white">
									<SessionsIcon />
								</CardComboIcon>
							</template>
						</CardCombo1>
					</div>

					<!-- two cards -->
					<div class="flex gap-5">
						<CardCombo2 title="Reports" centered class="basis-1/2">
							<template #icon>
								<CardComboIcon boxed :boxSize="50" :color="style['--secondary3-color']">
									<ReportsIcon />
								</CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Issues" centered class="basis-1/2">
							<template #icon>
								<CardComboIcon boxed :boxSize="50" :color="style['--secondary4-color']">
									<ErrorIcon />
								</CardComboIcon>
							</template>
						</CardCombo2>
					</div>

					<!-- map -->
					<div class="flex">
						<CardExtra7
							title="Top countries"
							:segmented="{
								content: true
							}"
						/>
					</div>

					<!-- timeline -->
					<div class="grow timeline-wrap">
						<CardExtra5
							long
							lazy
							hideImage
							title="Issues timeline"
							class="h-full overflow-hidden"
							:segmented="{
								content: true
							}"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import DemoChart from "@/components/charts/Apex.vue"
import DemoList from "@/components/list/List.vue"
import SessionsIcon from "@vicons/carbon/UserMultiple"
import UsersIcon from "@vicons/carbon/User"
import ReportsIcon from "@vicons/carbon/Report"
import ErrorIcon from "@vicons/carbon/Debug"
import ViewsIcon from "@vicons/carbon/View"
import ActivityIcon from "@vicons/carbon/Activity"
import UploadsIcon from "@vicons/carbon/CloudUpload"
import { useThemeStore } from "@/stores/theme"

import { computed } from "vue"

defineOptions({
	name: "Analytics"
})

const style: { [key: string]: any } = computed(() => useThemeStore().style)
const textSecondaryColor = computed<string>(() => style.value["--fg-secondary-color"])

const chartBg = computed<string>(() =>
	useThemeStore().isThemeDark ? style.value["--secondary1-color"] : style.value["--secondary1-color"]
)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/common.scss";

.page {
	.main-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		grid-template-rows: repeat(1, 1fr);
		grid-template-areas: "main main side";

		@media (max-width: 1200px) {
			display: flex;
			flex-direction: column;

			.timeline-wrap {
				min-height: 400px;
				display: flex;
				flex-direction: column;

				.n-card {
					flex-grow: 1;
				}
			}
		}
	}

	.main-col {
		grid-area: main;
		container-type: inline-size;

		.main-chart-wrap {
			height: 450px;
		}

		.four-cards-wrap {
			display: grid;
			grid-template-columns: repeat(4, minmax(0, 1fr));
			grid-template-rows: repeat(1, minmax(0, 1fr));

			@container (max-width: 1000px) {
				grid-template-columns: repeat(2, minmax(0, 1fr));
				grid-template-rows: repeat(2, minmax(0, 1fr));
			}

			@container (max-width: 460px) {
				grid-template-columns: repeat(1, minmax(0, 1fr));
				grid-template-rows: repeat(4, minmax(0, 1fr));
			}
		}
	}
	.side-col {
		grid-area: side;
	}
}
</style>
