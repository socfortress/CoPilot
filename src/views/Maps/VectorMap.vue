<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Vector Map</div>
			<div class="links">
				<a href="https://jvm-docs.vercel.app/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<n-card ref="card" contentStyle="padding:0">
			<n-spin :show="loading">
				<div style="height: 60vh; width: 100%; overflow: hidden" class="p-5">
					<vuevectormap
						v-if="!loading"
						ref="map"
						map="world"
						width="100%"
						height="100%"
						:options="options"
						@loaded="loaded"
						@regionTooltipShow="regionTooltipShow"
					></vuevectormap>
				</div>
			</n-spin>
		</n-card>
	</div>
</template>
<script setup lang="ts">
import { NCard, NSpin } from "naive-ui"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { computed, ref, watchEffect, watch } from "vue"
import { useResizeObserver, useWindowSize } from "@vueuse/core"
import { useThemeStore } from "@/stores/theme"

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)

function getOption() {
	return {
		map: "world_merc",
		regionStyle: { initial: { fill: style.value["--bg-body"] } },
		markers: [
			{ name: "Japan", coords: [36.48491549755618, 138.57517718545] },
			{ name: "Canada", coords: [56.1304, -106.3468] },
			{ name: "Greenland", coords: [71.7069, -42.6043] },
			{ name: "Egypt", coords: [26.8206, 30.8025], style: { fill: style.value["--secondary3-color"] } },
			{ name: "Brazil", coords: [-14.235, -51.9253], style: { fill: style.value["--secondary3-color"] } },
			{
				name: "Australia",
				coords: [-24.017090500279256, 134.57941295147762],
				style: { fill: style.value["--secondary3-color"] }
			},
			{ name: "United States", coords: [37.0902, -95.7129] },
			{ name: "Norway", coords: [60.472024, 8.468946], style: { fill: style.value["--secondary3-color"] } },
			{ name: "Ukraine", coords: [48.379433, 31.16558], style: { fill: style.value["--secondary3-color"] } }
		],
		lines: [
			{ from: "Japan", to: "Greenland" },
			{ from: "Japan", to: "United States" },
			{ from: "Japan", to: "Canada" },
			{ from: "Brazil", to: "Norway" },
			{ from: "Brazil", to: "Ukraine" },
			{ from: "Brazil", to: "Egypt" },
			{ from: "Brazil", to: "Australia" }
		],
		markerStyle: {
			initial: { fill: style.value["--primary-color"] },
			selected: { fill: style.value["--secondary1-color"] }
		},
		markerLabelStyle: {
			initial: {
				fontFamily: style.value["--font-family"],
				fontSize: 13,
				fill: style.value["--fg-color"]
			}
		},
		lineStyle: {
			strokeDasharray: "6 3 6",
			animation: true
		},
		labels: {
			markers: {
				render(marker: any) {
					return marker.name
				}
			}
		},
		showTooltip: true
	}
}

const options = ref(getOption())
const loading = ref(true)
const card = ref(null)
const loadingTimer = ref<NodeJS.Timeout | null>(null)
const { width } = useWindowSize()

function loaded(map: any) {
	useResizeObserver(card, () => {
		map.updateSize()
	})
}
function refresh() {
	loading.value = true
	if (loadingTimer.value) {
		clearTimeout(loadingTimer.value)
	}
	loadingTimer.value = setTimeout(() => {
		loading.value = false
	}, 1500)
	options.value = getOption()
}
function regionTooltipShow(_: any, tooltip: any) {
	tooltip.css({ backgroundColor: style.value["--primary-color"] })
}

watch(width, () => {
	refresh()
})

watchEffect(() => {
	refresh()
})
</script>

<style lang="scss">
.jvm-zoom-btn {
	width: 40px;
	height: 40px;
	font-size: 30px;
	text-align: center;
	line-height: 40px;
	padding: 0;
	color: var(--fg-color);
	background: var(--bg-body);
	border: 1px solid var(--border-color);

	&.jvm-zoomout {
		top: 60px;
	}
}
</style>
