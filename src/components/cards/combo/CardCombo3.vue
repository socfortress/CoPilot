<template>
	<n-card content-style="padding:0" hoverable>
		<div class="card-wrap flex flex-col">
			<div class="overlay" :class="{ twoSeries }">
				<div class="info">
					<div class="title">
						<span>Updated at</span>
						<span class="time">&nbsp;{{ updateTime }}</span>
					</div>

					<div class="box-wrapper flex">
						<CardCombo4
							title="Users"
							valString="248.3K"
							percentage
							:percentageProps="{
								value: 2.45,
								direction: 'up'
							}"
						/>
						<CardCombo4
							v-if="twoSeries"
							title="Sales"
							valString="$37.5K"
							percentage
							:percentageProps="{
								value: 1.96,
								direction: 'down'
							}"
						/>
					</div>
				</div>
				<div class="toolbar flex gap-2">
					<div v-if="twoSeries" class="flex gap-2">
						<n-button
							v-for="series of chartSeries"
							:key="series.name"
							@click="toggleSeries(series)"
							secondary
							:type="series.active ? 'default' : 'tertiary'"
						>
							<Icon :size="12" :color="series.color" :name="DotIcon"></Icon>
							<span class="ml-2">
								{{ series.name }}
							</span>
						</n-button>
					</div>
					<n-popselect
						v-model:value="chartTypeValue"
						:options="[
							{ label: 'Years', value: 'years' },
							{ label: 'Months', value: 'months' },
							{ label: 'Week', value: 'week' }
						]"
					>
						<n-button secondary>
							<Icon :size="14" :name="TimeIcon"></Icon>
							<span class="ml-2">
								{{ capitalized(chartTypeValue) }}
							</span>
						</n-button>
					</n-popselect>
				</div>
			</div>
			<n-spin :show="!loaded" class="chart grow">
				<DemoChart
					v-if="loaded"
					type="area"
					:seriesList="twoSeries ? ['Users', 'Sales'] : ['Users']"
					colorsSecondary
					:dataType="chartTypeValue"
					:strokeWidth="2"
					hideLegend
					:legendOffset="130"
					:fontColor="textSecondaryColor"
					@mounted="setChartContext"
				/>
			</n-spin>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NSpin, NButton, NPopselect } from "naive-ui"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import { computed, ref, toRefs, onMounted } from "vue"
import DemoChart, { type DataType, type VueApexChartsComponent } from "@/components/charts/DemoApex.vue"
import Icon from "@/components/common/Icon.vue"

const DotIcon = "carbon:circle-solid"
const TimeIcon = "carbon:time"

interface ChartSeries {
	active: boolean
	name: string
	color: string
}
type ChartSeriesList = ChartSeries[]

const props = withDefaults(
	defineProps<{
		oneSeries?: boolean
	}>(),
	{ oneSeries: false }
)
const { oneSeries } = toRefs(props)

const twoSeries = computed(() => !oneSeries.value)
const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
const textSecondaryColor = computed<string>(() => style.value["--fg-secondary-color"])
const loaded = ref(false)

const updateTime = ref(dayjs().format("DD-MM-YYYY HH:mm"))
const chartTypeValue = ref<DataType>("years")

const chartCTX = ref<VueApexChartsComponent | null>(null)
const chartSeries = ref<ChartSeriesList>([])

function setChartContext(ctx: VueApexChartsComponent) {
	chartCTX.value = ctx
	getSeries()
}

function toggleSeries(series: ChartSeries) {
	if (chartCTX.value) {
		series.active = !series.active
		chartCTX.value.toggleSeries(series.name)
	}
}

function getSeries() {
	const chartColors: string[] = chartCTX.value?.options?.colors || []
	chartSeries.value = (chartCTX.value?.series || []).map((s: any, index: number) => {
		return {
			active: true,
			name: s.name,
			color: chartColors[index % chartColors.length]
		}
	})
}

function capitalized(text: string) {
	const capitalizedFirst = text[0].toUpperCase()
	const rest = text.slice(1)

	return capitalizedFirst + rest
}

onMounted(() => {
	setTimeout(() => {
		loaded.value = true
	}, 1000)
})
</script>

<style scoped lang="scss">
.n-card {
	.card-wrap {
		position: relative;
		height: 100%;
		container-type: inline-size;

		.chart {
			overflow: hidden;
			width: 100%;
			padding-top: 40px;
			padding-bottom: 24px;

			:deep() {
				.n-spin-content {
					height: 100%;
					min-height: 300px;
				}
			}
		}

		.overlay {
			position: absolute;
			top: 0;
			left: 0;
			width: 100%;
			z-index: 1;
			padding: 26px;
			overflow: hidden;
			display: flex;
			justify-content: space-between;

			.info {
				width: fit-content;
				.title {
					color: var(--fg-secondary-color);
					letter-spacing: 0.1em;
					text-transform: uppercase;
					font-size: 10px;
					font-weight: bold;
				}
				.box-wrapper {
					gap: 40px;
				}
			}
			&.twoSeries {
				.info {
					.box-wrapper {
						margin-top: 20px;
					}
				}
			}
		}

		@container (max-width: 650px) {
			.overlay {
				&.twoSeries {
					flex-direction: column-reverse;
				}

				.info {
					.title {
						display: none;
					}
				}
			}
		}

		@container (max-width: 280px) {
			.overlay {
				flex-direction: column-reverse;

				.info {
					.box-wrapper {
						margin-top: 20px;
					}
				}
			}
		}
	}
}
</style>
