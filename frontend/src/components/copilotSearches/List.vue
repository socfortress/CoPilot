<template>
	<div class="@container flex flex-col gap-4">
		<n-alert type="info">
			CoPilot Searches provides pre-built detection queries for threat hunting in your Wazuh indexer. See
			<a href="https://github.com/socfortress/CoPilot-Search-Queries" target="_blank">
				https://github.com/socfortress/CoPilot-Search-Queries
			</a>
			for details.
		</n-alert>

		<n-tabs
			v-model:value="viewMode"
			type="segment"
			animated
			tab-class="px-5!"
			class="[&_.n-tabs-nav]:mx-auto [&_.n-tabs-nav]:min-w-70"
		>
			<template #suffix>
				<n-button type="primary" size="small" @click="createRule">
					<template #icon><Icon :name="AddIcon" :size="16" /></template>
					Create rule
				</n-button>
			</template>
			<n-tab-pane name="grid" tab="Rules" display-directive="show:lazy">
				<GridView />
			</n-tab-pane>
			<n-tab-pane name="matrix" tab="Matrix" display-directive="show:lazy">
				<MatrixView />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NAlert, NButton, NTabPane, NTabs } from "naive-ui"
import { onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import GridView from "./GridView/GridView.vue"
import MatrixView from "./MatrixView/MatrixView.vue"

const AddIcon = "carbon:add"
const viewMode = ref<"grid" | "matrix">("grid")

const route = useRoute()
const router = useRouter()

function createRule() {
	router.push({ name: "CopilotSearchEditor" })
}

onMounted(() => {
	const v = route.query.view
	if (v === "matrix" || v === "grid") viewMode.value = v
})

watch(viewMode, v => {
	if (route.query.view === v) return
	const next = { ...route.query }
	if (v === "grid") {
		delete next.view
		delete next.technique
		delete next.sub
	} else {
		next.view = v
	}
	router.replace({ query: next })
})
</script>
