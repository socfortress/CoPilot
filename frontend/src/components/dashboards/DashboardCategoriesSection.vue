<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center justify-between">
			<p class="text-secondary text-sm">Dashboard Categories</p>
			<span class="text-secondary text-sm">{{ categories.length }} available</span>
		</div>

		<n-spin :show="loadingCategories">
			<div
				v-if="categories.length"
				class="grid grid-cols-1 gap-3 @xl:grid-cols-2 @3xl:grid-cols-3 @6xl:grid-cols-4"
			>
				<DashboardCategoryCard
					v-for="cat in categories"
					:key="cat.id"
					:category="cat"
					:selected="selectedCategoryId === cat.id"
					@select="selectCategory(cat.id)"
				/>
			</div>
			<n-empty v-else-if="!loadingCategories" description="No dashboard categories found" />
		</n-spin>

		<n-drawer
			v-model:show="showCategoryDrawer"
			display-directive="show"
			:width="760"
			class="max-w-[92vw]"
			:trap-focus="false"
		>
			<n-drawer-content :title="drawerTitle" closable :native-scrollbar="false">
				<DashboardCategoryDrawerContent
					v-model:selected-event-source-id="selectedEventSourceId"
					:category="selectedCategory"
					:category-meta="selectedCategoryMeta ?? null"
					:loading-templates
					:selected-customer-code
					:loading-event-sources
					:event-sources-list
					:selected-category-id
					:enabled-dashboards
					@refresh-enabled-dashboards="emit('refreshEnabledDashboards')"
				/>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { DashboardCategory, DashboardCategoryWithTemplates, EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import { NDrawer, NDrawerContent, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import DashboardCategoryCard from "./DashboardCategoryCard.vue"
import DashboardCategoryDrawerContent from "./DashboardCategoryDrawerContent.vue"

const props = defineProps<{
	selectedCustomerCode: string | null
	eventSourcesList: EventSource[]
	loadingEventSources: boolean
	enabledDashboards: EnabledDashboard[]
}>()

const emit = defineEmits<{
	refreshEnabledDashboards: []
}>()

const message = useMessage()

const loadingCategories = ref(false)
const categories = ref<DashboardCategory[]>([])
const selectedCategoryId = ref<string | null>(null)
const selectedCategory = ref<DashboardCategoryWithTemplates | null>(null)
const loadingTemplates = ref(false)
const selectedEventSourceId = ref<number | null>(null)

const selectedCategoryMeta = computed(() =>
	selectedCategoryId.value ? categories.value.find(cat => cat.id === selectedCategoryId.value) : null
)

const drawerTitle = computed(() => selectedCategory.value?.title ?? selectedCategoryMeta.value?.title ?? "Category")

const showCategoryDrawer = computed({
	get: () => selectedCategoryId.value !== null,
	set(open: boolean) {
		if (!open) {
			selectedCategoryId.value = null
			selectedCategory.value = null
		}
	}
})

function getCategories() {
	loadingCategories.value = true
	Api.siem
		.getDashboardCategories()
		.then(res => {
			if (res.data.success) {
				categories.value = res.data?.categories || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCategories.value = false
		})
}

function selectCategory(categoryId: string) {
	if (selectedCategoryId.value === categoryId) {
		showCategoryDrawer.value = false
		return
	}

	selectedCategoryId.value = categoryId
	selectedCategory.value = null
	loadingTemplates.value = true

	Api.siem
		.getDashboardCategory(categoryId)
		.then(res => {
			if (res.data.success) {
				selectedCategory.value = res.data.category
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingTemplates.value = false
		})
}

watch(
	() => props.selectedCustomerCode,
	() => {
		selectedEventSourceId.value = null
	}
)

watch(
	() => props.eventSourcesList,
	sources => {
		if (!selectedEventSourceId.value) return

		const hasSelectedSource = sources.some(source => source.enabled && source.id === selectedEventSourceId.value)

		if (!hasSelectedSource) {
			selectedEventSourceId.value = null
		}
	}
)

onBeforeMount(() => {
	getCategories()
})
</script>
