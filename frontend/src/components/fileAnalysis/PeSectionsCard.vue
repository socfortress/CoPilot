<template>
	<!--
		The PE section table, rebuilt as a chart plus a list.

		A section header answers two questions at a glance — where the file's bulk
		sits, and whether any part of it looks packed — and a four-column data grid
		answers neither: the sizes are raw byte counts you have to divide in your
		head, and entropy is a bare float with no scale to read it against.

		So the shares become a donut (one look tells you a resource section is most
		of the file), and each row carries an entropy meter on its 0–8 scale with the
		packing threshold marked, instead of a number you have to know how to grade.
	-->
	<CollapsibleCard :collapsible="false">
		<template #header>
			<span :class="SECTION_LABEL">Sections</span>
			<span class="text-tertiary font-mono text-xs">{{ sections.length }}</span>
			<n-tag v-if="packedCount" size="small" type="warning" round :bordered="false">
				{{ packedCount }} packed or encrypted
			</n-tag>
		</template>

		<div class="bg-border grid gap-px overflow-hidden @3xl:grid-cols-[minmax(0,17rem)_1fr]">
			<div class="bg-secondary flex flex-col items-center gap-1 overflow-hidden p-4">
				<!-- The height goes in :style, not a class: vue-echarts puts height:100% inline
				     on its root, and an inline rule beats a utility class — a class-only height
				     collapses the chart to whatever the row happens to be. -->
				<v-chart
					class="w-full"
					:style="{ height: CHART_HEIGHT, width: '100%' }"
					autoresize
					:option="chartOption"
				/>
				<span class="text-tertiary text-xs">On-disk size by section</span>
			</div>

			<div class="bg-secondary divide-border @container flex flex-col divide-y">
				<div
					v-for="row of rows"
					:key="row.key"
					class="flex flex-col flex-wrap gap-x-5 gap-y-3 p-3 @2xl:flex-row @2xl:flex-nowrap @2xl:items-center"
				>
					<div class="flex min-w-0 grow items-center gap-2.5">
						<span class="size-2.5 shrink-0 rounded-full" :style="{ backgroundColor: row.color }" />
						<span class="text-default truncate font-mono text-sm">{{ row.name }}</span>
						<span class="text-tertiary shrink-0 font-mono text-xs">{{ row.share }}</span>
					</div>

					<div class="text-tertiary flex shrink-0 items-baseline gap-1.5 font-mono text-xs">
						<span class="text-default">{{ row.raw }}</span>
						<span>on disk</span>
						<span class="text-secondary ml-1">{{ row.virtual }}</span>
						<span>in memory</span>
					</div>

					<!-- The meter is the point: entropy only means something against its
					     0–8 ceiling, and the tick marks where packing starts. -->
					<div class="flex w-full shrink-0 items-center gap-2 @2xl:w-44">
						<div class="bg-border relative h-1.5 grow overflow-hidden rounded-full">
							<div class="h-full rounded-full" :class="row.barClass" :style="{ width: row.barWidth }" />
							<span class="bg-default/60 absolute inset-y-0 w-px" :style="{ left: PACKED_MARK }" />
						</div>
						<span class="shrink-0 font-mono text-xs" :class="row.valueClass">
							{{ row.entropy }}
						</span>
					</div>
				</div>
			</div>
		</div>
	</CollapsibleCard>
</template>

<script setup lang="ts">
import type { PieSeriesOption } from "echarts/charts"
import type { TooltipComponentOption } from "echarts/components"
import type { ComposeOption } from "echarts/core"
import type { InspectorSection } from "@/types/file-analysis"
import { PieChart } from "echarts/charts"
import { GraphicComponent, TooltipComponent } from "echarts/components"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { NTag } from "naive-ui"
import { computed } from "vue"
import VChart from "vue-echarts"
import {
	buildChartTooltipGlassBase,
	CHART_COLORS,
	chartTooltipThemeFromStyle,
	formatChartTooltipWithMarker
} from "@/components/common/charts"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useThemeStore } from "@/stores/theme"
import { formatBytes } from "@/utils/format"

const props = defineProps<{ sections: InspectorSection[] }>()

use([CanvasRenderer, PieChart, TooltipComponent, GraphicComponent])

type ChartOption = ComposeOption<TooltipComponentOption | PieSeriesOption>

const CHART_HEIGHT = "12rem"

/** Shannon entropy over bytes cannot exceed 8 bits; the meter is drawn against that. */
const ENTROPY_MAX = 8
/** Above this, a section is compressed, encrypted or packed rather than plain code. */
const PACKED_THRESHOLD = 7.2
/** Elevated but unremarkable on its own — packed resources are common in benign files. */
const ELEVATED_THRESHOLD = 6.5
const PACKED_MARK = `${(PACKED_THRESHOLD / ENTROPY_MAX) * 100}%`

const themeStore = useThemeStore()

const totalRaw = computed(() => props.sections.reduce((sum, s) => sum + (s.rawsize || 0), 0))

const packedCount = computed(() => props.sections.filter(s => s.entropy >= PACKED_THRESHOLD).length)

const rows = computed(() =>
	props.sections.map((s, i) => {
		const color = CHART_COLORS[i % CHART_COLORS.length]
		const packed = s.entropy >= PACKED_THRESHOLD
		const elevated = s.entropy >= ELEVATED_THRESHOLD
		return {
			// A malformed PE can carry two sections with the same name, so the index
			// stays in the key — a duplicate name must not collapse two rows into one.
			key: `${i}-${s.name}`,
			name: s.name || "—",
			color,
			share: totalRaw.value ? `${((s.rawsize / totalRaw.value) * 100).toFixed(1)}%` : "—",
			raw: formatBytes(s.rawsize),
			virtual: formatBytes(s.vsize),
			entropy: s.entropy.toFixed(2),
			barWidth: `${Math.min(100, (s.entropy / ENTROPY_MAX) * 100)}%`,
			barClass: packed ? "bg-error" : elevated ? "bg-warning" : "bg-primary",
			valueClass: packed ? "text-error" : elevated ? "text-warning" : "text-secondary"
		}
	})
)

const chartOption = computed((): ChartOption => {
	const style = themeStore.style
	const fg = style["fg-default-color"]
	const ff = style["font-family"]

	return {
		backgroundColor: "transparent",
		color: [...CHART_COLORS],
		tooltip: {
			...buildChartTooltipGlassBase(chartTooltipThemeFromStyle(style)),
			formatter: params => {
				if (!params || Array.isArray(params)) return ""
				const value = typeof params.value === "number" ? params.value : 0
				const pct = typeof params.percent === "number" ? params.percent : 0
				const section = props.sections[params.dataIndex ?? 0]
				return formatChartTooltipWithMarker({
					marker: params.marker,
					color: params.color,
					title: params.name ?? "",
					lines: [
						`<strong>${formatBytes(value)}</strong> on disk (${pct.toFixed(1)}%)`,
						`entropy ${section?.entropy?.toFixed(2) ?? "—"}`
					]
				})
			}
		},
		// The total belongs in the hole rather than in a caption: the donut is a
		// breakdown of exactly that number, and reading it means reading the whole.
		graphic: [
			{
				type: "text",
				left: "center",
				top: "middle",
				style: {
					text: `${formatBytes(totalRaw.value)}\n\ntotal`,
					fill: fg,
					fontSize: 13,
					fontFamily: ff,
					textAlign: "center",
					textVerticalAlign: "middle"
				}
			}
		],
		series: [
			{
				name: "On-disk size",
				type: "pie",
				radius: ["64%", "88%"],
				center: ["50%", "50%"],
				avoidLabelOverlap: true,
				label: { show: false },
				labelLine: { show: false },
				itemStyle: { borderWidth: 2, borderColor: style["bg-secondary-color"] },
				data: props.sections.map(s => ({ name: s.name || "—", value: s.rawsize || 0 }))
			}
		]
	}
})
</script>
