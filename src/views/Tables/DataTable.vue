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
			<Empty />
			<Expand />
			<LargeData />
			<Editable />
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import Basic from "./data-tables-components/Basic.vue"
import Merge from "./data-tables-components/Merge.vue"
import Sorting from "./data-tables-components/Sorting.vue"
import Draggable from "./data-tables-components/Draggable.vue"
import Selection from "./data-tables-components/Selection.vue"
import Empty from "./data-tables-components/Empty.vue"
import Expand from "./data-tables-components/Expand.vue"
import LargeData from "./data-tables-components/LargeData.vue"
import Editable from "./data-tables-components/Editable.vue"
</script>

<style scoped lang="scss">
.components-list {
	grid-template-columns: none;

	:deep() {
		.n-data-table-td,
		.n-data-table-th {
			white-space: nowrap;
		}

		.n-data-table-td--selection,
		.n-data-table-th--selection,
		.n-data-table-th--expand,
		.n-data-table-td--expand {
			padding: var(--n-td-padding);
			z-index: 2;
		}
	}
}
</style>
