<template>
	<div class="page">
		<div class="page-header">
			<div class="title">ChartJS</div>
			<div class="links">
				<a href="https://vue-chartjs.org/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">
					<Icon :name="ExternalIcon" :size="16" />
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
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

import Bar from "@/components/charts/demo-pages/chartjs-components/Bar.vue"
import Line from "@/components/charts/demo-pages/chartjs-components/Line.vue"
</script>

<style scoped lang="scss">
.components-list {
	grid-template-columns: none;
}
</style>
