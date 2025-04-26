<template>
	<n-tabs type="line" animated :tabs-padding="24" class="grow" pane-wrapper-class="flex grow flex-col">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex grow flex-col">
			<div class="p-5 pt-3">
				<div class="flex items-stretch gap-4">
					<CardKV size="lg" class="basis-1/2">
						<template #key>Status</template>
						<template #value>switch...</template>
					</CardKV>
					<CardKV size="lg" class="basis-1/2">
						<template #key>Creator</template>
						<template #value>
							<div class="flex flex-col gap-2">
								<div>by: {{ entity.created_by }}</div>
								<div>at: {{ formatDate(entity.created_at, dFormats.datetimesec) }}</div>
							</div>
						</template>
					</CardKV>
				</div>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Fields" tab="Fields" display-directive="show:lazy">
			<div class="p-7 pt-4">Fields...</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules.d"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NTabPane, NTabs } from "naive-ui"
import { toRefs } from "vue"

const props = defineProps<{
	entity: ExclusionRule
}>()

const { entity } = toRefs(props)

const dFormats = useSettingsStore().dateFormat

/*
const emit = defineEmits<{
	(e: "deleted", value: ExclusionRule): void
	(e: "updated", value: ExclusionRule): void
}>()

function updateQuery(updatedQuery: SigmaQuery) {
	emit("updated", updatedQuery)
	}
	*/
</script>
