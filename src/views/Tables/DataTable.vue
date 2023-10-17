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
				>
					<Icon :name="ExternalIcon" :size="16" />
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
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
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
