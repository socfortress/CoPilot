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
			:width="960"
			class="max-w-[92vw]"
			:trap-focus="false"
		>
			<n-drawer-content closable :native-scrollbar="false">
				<template #header>
					<div class="flex w-full items-center justify-between gap-3 pr-6">
						<div class="flex min-w-0 items-center gap-2">
							<div
								v-if="selectedCategoryMeta"
								class="flex shrink-0 items-center justify-center"
								:style="{ color: selectedCategoryMeta.color }"
							>
								<Icon :name="getDashboardIcon(selectedCategoryMeta.icon)" :size="19" />
							</div>
							<div class="min-w-0">
								<p class="truncate font-medium">{{ drawerTitle }}</p>
								<p v-if="selectedCategory" class="text-secondary text-xs">
									{{ selectedCategory.templates.length }} template{{
										selectedCategory.templates.length !== 1 ? "s" : ""
									}}
								</p>
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
				</template>

				<n-spin :show="loadingTemplates">
					<div
						v-if="selectedCategory?.templates.length"
						class="grid grid-cols-1 gap-3 @xl:grid-cols-2 @3xl:grid-cols-3"
					>
						<DashboardTemplateCard
							v-for="tpl in selectedCategory.templates"
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
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { DashboardCategory, DashboardCategoryWithTemplates, EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import { NDrawer, NDrawerContent, NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import DashboardCategoryCard from "./DashboardCategoryCard.vue"
import DashboardTemplateCard from "./DashboardTemplateCard.vue"
import { getDashboardIcon } from "./utils"

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

const eventSourceOptions = computed(() =>
	props.eventSourcesList
		.filter(source => source.enabled)
		.map(source => ({
			label: `${source.name} (${source.event_type})`,
			value: source.id
		}))
)

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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
