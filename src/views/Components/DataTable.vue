<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Data Table</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/data-table"
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
			<Basic />
			<Merge />
			<Sorting />
			<Draggable />
			<Selection />
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon } from "naive-ui"
import Basic from "./data-table-components/Basic.vue"
import Merge from "./data-table-components/Merge.vue"
import Sorting from "./data-table-components/Sorting.vue"
import Draggable from "./data-table-components/Draggable.vue"
import Selection from "./data-table-components/Selection.vue"
import ExternalIcon from "@vicons/tabler/ExternalLink"
</script>

<style lang="scss" scoped>
.components-list {
	grid-template-columns: none;
}
</style>
