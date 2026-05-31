<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-3">
			<div class="flex min-w-0 items-center gap-2">
				<div
					v-if="categoryMeta"
					class="flex shrink-0 items-center justify-center"
					:style="{ color: categoryMeta.color }"
				>
					<Icon :name="getDashboardIcon(categoryMeta.icon)" :size="19" />
				</div>
				<div v-if="category">
					{{ category.templates.length }} template{{ category.templates.length !== 1 ? "s" : "" }}
				</div>
			</div>

			<n-select
				v-model:value="selectedEventSourceId"
				:options="eventSourceOptions"
				placeholder="Select Event Source"
				filterable
				:loading="loadingEventSources"
				:disabled="!selectedCustomerCode"
				clearable
				size="small"
				:consistent-menu-width="false"
				class="w-48! shrink-0"
			/>
		</div>

		<n-spin :show="loadingTemplates">
			<div v-if="category?.templates.length" class="grid grid-cols-1 gap-3 @xl:grid-cols-2 @3xl:grid-cols-3">
				<DashboardTemplateCard
					v-for="tpl in category.templates"
					:key="tpl.id"
					:template="tpl"
					:selected-customer-code
					:selected-event-source-id
					:selected-category-id
					:enabled-dashboards
					disabled-tooltip-text="Select an event source first"
					@refresh-enabled-dashboards="emit('refreshEnabledDashboards')"
				/>
			</div>
			<n-empty v-else-if="!loadingTemplates" description="No templates in this category" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { DashboardCategory, DashboardCategoryWithTemplates, EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import { NEmpty, NSelect, NSpin } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import DashboardTemplateCard from "./DashboardTemplateCard.vue"
import { getDashboardIcon } from "./utils"

const props = defineProps<{
	category: DashboardCategoryWithTemplates | null
	categoryMeta: DashboardCategory | null
	loadingTemplates: boolean
	selectedCustomerCode: string | null
	loadingEventSources: boolean
	eventSourcesList: EventSource[]
	selectedCategoryId: string | null
	enabledDashboards: EnabledDashboard[]
}>()

const emit = defineEmits<{
	refreshEnabledDashboards: []
}>()

const selectedEventSourceId = defineModel<number | null>("selectedEventSourceId", { default: null })

const eventSourceOptions = computed(() =>
	props.eventSourcesList
		.filter(source => source.enabled)
		.map(source => ({
			label: `${source.name} (${source.event_type})`,
			value: source.id
		}))
)
</script>
