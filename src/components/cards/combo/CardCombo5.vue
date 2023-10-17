<template>
	<n-card>
		<div class="card-wrap flex gap-14 justify-between overflow-hidden" ref="trigger">
			<div class="info-box flex flex-col gap-4 grow">
				<div class="title">Users clusters</div>
				<div class="list flex flex-col gap-3">
					<CardCombo4
						title="Active users"
						size="small"
						valString="173.1K"
						cardWrap
						:percentageProps="{
							value: 2.45,
							direction: 'up'
						}"
					>
						<template #icon>
							<CardComboIcon boxed :iconName="ActiveUsersIcon" />
						</template>
					</CardCombo4>

					<CardCombo4
						title="Canceled users"
						valString="56.3K"
						size="small"
						cardWrap
						:percentageProps="{
							value: 2.45,
							direction: 'up'
						}"
					>
						<template #icon>
							<CardComboIcon
								boxed
								:color="style['--secondary4-color']"
								:iconName="CanceledUsersIcon"
							></CardComboIcon>
						</template>
					</CardCombo4>

					<CardCombo4
						title="AFK users"
						valString="98.6K"
						size="small"
						cardWrap
						:percentageProps="{
							value: 2.45,
							direction: 'up'
						}"
					>
						<template #icon>
							<CardComboIcon
								boxed
								:color="style['--secondary3-color']"
								:iconName="AFKUsersIcon"
							></CardComboIcon>
						</template>
					</CardCombo4>
				</div>
			</div>
			<div class="chart-box flex flex-col gap-4 overflow-hidden" ref="chartBox">
				<div class="title">Users target</div>

				<div class="chart overflow-hidden">
					<Apex type="radialBar" height="270" width="270" :options="chartOptions" :series="series"></Apex>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { ref, computed, watchEffect } from "vue"
import { useResizeObserver } from "@vueuse/core"
import Apex from "@/components/charts/Apex.vue"
import { useThemeStore } from "@/stores/theme"

const ActiveUsersIcon = "carbon:activity"
const CanceledUsersIcon = "carbon:trash-can"
const AFKUsersIcon = "carbon:pause"

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
const secondaryColors = computed(() => Object.values(useThemeStore().secondaryColors))
const palette = computed<string[]>(() => new Array(4).fill(secondaryColors.value).flat())
const trigger = ref(null)
const chartBox = ref<HTMLElement | null>(null)

const series = ref([54, 67, 93])

function getOption(width?: number) {
	return {
		chart: {
			type: "radialBar",
			parentHeightOffset: 0,
			width: width && width < 270 ? width : 270,
			height: width && width < 270 ? width : 270
		},
		grid: {
			padding: {
				top: width && width < 270 ? 0 : -30,
				right: width && width < 270 ? 0 : -39,
				bottom: width && width < 270 ? 0 : -30,
				left: width && width < 270 ? 0 : -39
			}
		},
		plotOptions: {
			radialBar: {
				offsetY: 0,
				startAngle: 0,
				endAngle: 270,
				hollow: {
					size: "45%",
					background: "transparent",
					image: undefined
				},
				track: {
					margin: 8,
					show: true,
					background: style.value["--bg-body"],
					strokeWidth: "100%",
					opacity: 1
				},
				dataLabels: {
					name: {
						show: true,
						fontSize: "15px",
						fontFamily: style.value["--font-family"],
						color: style.value["--fg-color"],
						offsetY: -10
					},
					value: {
						show: true,
						offsetY: 1,
						fontSize: "22px",
						fontWeight: 700,
						fontFamily: style.value["--font-family-display"],
						color: style.value["--fg-color"]
					}
				}
			}
		},
		colors: palette.value,
		labels: ["Men", "Women", "Others"],
		legend: {
			show: true,
			floating: true,
			fontSize: "12px",
			fontFamily: style.value["--font-family"],
			position: "left",
			offsetX: -30,
			offsetY: -26,
			labels: {
				useSeriesColors: true
			},
			markers: {
				size: 0
			},
			formatter: function (seriesName: string, opts: any) {
				return ` <span>${seriesName}:  <strong>${opts.w.globals.series[opts.seriesIndex]}</strong></span>`
			},
			itemMargin: {
				vertical: 3
			}
		}
	}
}

const chartOptions = ref(getOption())

useResizeObserver(trigger, () => {
	const entry = chartBox.value
	chartOptions.value = getOption(entry?.offsetWidth)
})

watchEffect(async () => {
	chartOptions.value = getOption()
})
</script>

<style scoped lang="scss">
.n-card {
	container-type: inline-size;

	.card-wrap {
		height: 100%;

		.title {
			text-transform: uppercase;
			color: var(--fg-secondary-color);
			font-weight: 700;
			letter-spacing: 0.4px;
			text-transform: uppercase;
			font-size: 10px;
		}

		.info-box {
			max-width: 320px;
		}

		.chart-box {
			max-width: 100%;
			.chart {
				height: 270px;
				width: 270px;
				max-width: 100%;

				.vue-apexcharts {
					display: flex;
					justify-content: center;
					:deep() {
						.apexcharts-legend-series {
							.apexcharts-legend-marker {
								width: 10px !important;
								height: 10px !important;
							}
							.apexcharts-legend-text {
								color: var(--fg-color) !important;
							}
						}
					}
				}
			}
		}

		@container (max-width:570px) {
			flex-direction: column;
			gap: 50px;

			.info-box {
				max-width: 100%;
			}

			.chart-box {
				align-self: center;
				.title {
					display: none;
				}
			}
		}
	}
}
</style>
