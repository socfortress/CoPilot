<template>
	<div class="page">
		<div class="page-header">
			<div class="title">ChartJS</div>
			<div class="links">
				<a
					href="https://vue-chartjs.org/"
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
			<Bar />
			<Line />
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import Bar from "./chartjs-components/Bar.vue"
import Line from "./chartjs-components/Line.vue"
</script>

<style scoped lang="scss">
.components-list {
	grid-template-columns: none;
}
</style>
