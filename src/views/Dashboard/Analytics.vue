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
								<CardComboIcon :iconName="UsersIcon" boxed></CardComboIcon>
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
								<CardComboIcon :iconName="ViewsIcon" boxed></CardComboIcon>
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
								<CardComboIcon :iconName="ActivityIcon" boxed></CardComboIcon>
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
								<CardComboIcon :iconName="UploadsIcon" boxed></CardComboIcon>
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
								<CardComboIcon :iconName="SessionsIcon" boxed color="white"></CardComboIcon>
							</template>
						</CardCombo1>
					</div>

					<!-- two cards -->
					<div class="flex gap-5">
						<CardCombo2 title="Reports" centered class="basis-1/2">
							<template #icon>
								<CardComboIcon
									:iconName="ReportsIcon"
									boxed
									:boxSize="50"
									:color="style['--secondary3-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Issues" centered class="basis-1/2">
							<template #icon>
								<CardComboIcon
									:iconName="ErrorIcon"
									boxed
									:boxSize="50"
									:color="style['--secondary4-color']"
								></CardComboIcon>
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
import DemoChart from "@/components/charts/DemoApex.vue"
import DemoList from "@/components/list/List.vue"
import { useThemeStore } from "@/stores/theme"
import { computed } from "vue"

const SessionsIcon = "carbon:user-multiple"
const UsersIcon = "carbon:user"
const ReportsIcon = "carbon:report"
const ErrorIcon = "carbon:debug"
const ViewsIcon = "carbon:view"
const ActivityIcon = "carbon:activity"
const UploadsIcon = "carbon:cloud-upload"

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
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
