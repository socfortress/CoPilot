<template>
	<div class="page">
		<div class="page-header">
			<div class="title">ApexCharts</div>
			<div class="links">
				<a
					href="https://apexcharts.com/"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<Brush />
			<Realtime />
			<Sync />
			<Column />
			<Bar />
			<div class="flex lg:flex-row flex-col gap-5">
				<div class="lg:basis-1/2 basis-full lg:min-h-full">
					<Pie />
				</div>
				<div class="lg:basis-1/2 basis-full lg:min-h-full">
					<Radar />
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import Brush from "./apex-charts-components/Brush.vue"
import Realtime from "./apex-charts-components/Realtime.vue"
import Sync from "./apex-charts-components/Sync.vue"
import Column from "./apex-charts-components/Column.vue"
import Bar from "./apex-charts-components/Bar.vue"
import Pie from "./apex-charts-components/Pie.vue"
import Radar from "./apex-charts-components/Radar.vue"
</script>

<style scoped lang="scss">
.components-list {
	grid-template-columns: none;
}
</style>
