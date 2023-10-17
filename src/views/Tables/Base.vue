<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Table Base</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/table"
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
			<CardCodeExample title="Basic">
				<n-scrollbar x-scrollable style="width: 100%">
					<TableBase class="table-min-width" :bordered="false" />
				</n-scrollbar>
			</CardCodeExample>

			<CardCodeExample title="Bordered">
				<n-scrollbar x-scrollable style="width: 100%">
					<TableBase class="table-min-width" :bordered="true" />
				</n-scrollbar>
			</CardCodeExample>

			<CardCodeExample title="Size">
				<n-scrollbar x-scrollable style="width: 100%">
					<TableBase class="table-min-width mb-4" size="small" />
					<TableBase class="table-min-width" size="large" />
				</n-scrollbar>
			</CardCodeExample>

			<CardCodeExample title="Single column">
				<n-scrollbar x-scrollable style="width: 100%">
					<TableBase class="table-min-width" single-column :single-line="false" />
				</n-scrollbar>
			</CardCodeExample>

			<CardCodeExample title="Single line">
				<n-scrollbar x-scrollable style="width: 100%">
					<TableBase class="table-min-width" />
				</n-scrollbar>
			</CardCodeExample>

			<CardCodeExample title="Stripe">
				<n-scrollbar x-scrollable style="width: 100%">
					<TableBase class="table-min-width" striped />
				</n-scrollbar>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import TableBase from "@/components/tables/Base.vue"
</script>

<style scoped lang="scss">
.components-list {
	grid-template-columns: none;
}

.table-min-width {
	min-width: 480px;
}
</style>
