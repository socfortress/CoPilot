<template>
	<div class="uncommitted-entries-wrap flex flex-col gap-3">
		<div class="uncommitted-entries">
			<div class="chart grow">
				<div class="label flex items-center gap-3">
					<Icon :name="DangerIcon" v-if="isWarning"></Icon>
					<span>Uncommitted Journal Entries</span>
				</div>
				<apexchart height="70" :options="options" :series="series" ref="chart"></apexchart>
			</div>
			<div class="value flex flex-col justify-center" :class="{ warning: isWarning }">
				<span>{{ value }}</span>
			</div>
		</div>
		<div class="footer">
			<n-button type="primary" ghost icon-placement="right" @click="gotoGraylogManagement('messages')">
				<template #icon>
					<Icon :name="LinkIcon" :size="14"></Icon>
				</template>
				See messages
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NButton } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import { useThemeStore } from "@/stores/theme"
import dayjs from "@/utils/dayjs"
import "@/assets/scss/apexchart-override.scss"
import { watch } from "vue"
import { usHealthcheckStore } from "@/stores/healthcheck"
import apexchart from "vue3-apexcharts"
import { useGoto } from "@/composables/useGoto"

const UNCOMMITTED_JOURNAL_ENTRIES_THRESHOLD = usHealthcheckStore().uncommittedJournalEntriesThreshold

const props = defineProps<{
	value: number
}>()
const { value } = toRefs(props)

const LinkIcon = "carbon:launch"
const DangerIcon = "majesticons:exclamation-line"

const style = computed(() => useThemeStore().style)
const isThemeDark = computed(() => useThemeStore().isThemeDark)
const { gotoGraylogManagement } = useGoto()

const isWarning = computed<boolean>(() => {
	return value.value > UNCOMMITTED_JOURNAL_ENTRIES_THRESHOLD
})

const series = ref<{ name: string; data: [Date, number][] }[]>([
	{
		name: "Entries",
		data: []
	}
])

const serieLength = computed<number>(() => series.value[0].data.length || 0)

function getOptions() {
	return {
		chart: {
			height: 70,
			type: "area",
			sparkline: {
				enabled: true
			},
			animations: {
				enabled: serieLength.value < 100,
				easing: "linear",
				dynamicAnimation: {
					speed: 200
				}
			},
			toolbar: {
				show: false
			},
			zoom: {
				enabled: false
			}
		},
		dataLabels: {
			enabled: false
		},
		stroke: {
			curve: "straight",
			width: 3
		},
		xaxis: {
			type: "datetime"
		},
		colors: [style.value["primary-color"]],
		tooltip: {
			x: {
				formatter: (time: number) => {
					return dayjs(time).format("HH:mm:ss")
				}
			},
			y: {
				formatter: (val: number | string) => {
					return val || "&nbsp;0"
				}
			},
			style: {
				fontFamily: style.value["font-family-mono"]
			},
			theme: isThemeDark.value ? "dark" : "light"
		}
	}
}

const options = ref(getOptions())

watch(value, val => {
	if (serieLength.value > 100) {
		series.value[0].data.shift()

		if (options.value.chart.animations.enabled) {
			options.value = getOptions()
		}
	}
	series.value[0].data.push([new Date(), val])
})

watch(isThemeDark, () => {
	options.value = getOptions()
})
</script>

<style lang="scss" scoped>
.uncommitted-entries-wrap {
	width: 100%;

	.uncommitted-entries {
		background-color: var(--bg-color);
		display: flex;
		border-radius: var(--border-radius);
		border: var(--border-small-050);

		.label {
			padding: 18px 22px;
			font-size: 18px;
			flex-grow: 1;
			font-weight: 700;

			i {
				color: var(--secondary3-color);
			}
		}
		.value {
			padding: 18px 22px;
			background-color: var(--bg-secondary-color);
			font-size: 20px;
			font-family: var(--font-family-mono);
			min-width: 80px;
			text-align: center;
			border-top-right-radius: var(--border-radius);
			border-bottom-right-radius: var(--border-radius);

			&.warning {
				color: var(--secondary3-color);
				background-color: var(--secondary3-opacity-005-color);
			}
		}
	}
}
</style>
