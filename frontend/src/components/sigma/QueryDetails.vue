<template>
	<n-tabs type="line" animated :tabs-padding="24" v-if="query" class="grow" pane-wrapper-class="flex flex-col grow">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex flex-col grow">
			<div class="pt-1">
				<QueryOverview :query @updated="updateQuery($event)" @deleted="emit('deleted', query)" />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Rule Query" tab="Rule Query" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<CodeSource :code="query.rule_query" lang="sql" />
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import { defineAsyncComponent, toRefs } from "vue"
import { NTabs, NTabPane } from "naive-ui"
import type { SigmaQuery } from "@/types/sigma.d"

const QueryOverview = defineAsyncComponent(() => import("./QueryOverview.vue"))
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const props = defineProps<{
	query: SigmaQuery
}>()
const { query } = toRefs(props)

const emit = defineEmits<{
	(e: "deleted", value: SigmaQuery): void
	(e: "updated", value: SigmaQuery): void
}>()

function updateQuery(updatedQuery: SigmaQuery) {
	emit("updated", updatedQuery)
}
</script>
