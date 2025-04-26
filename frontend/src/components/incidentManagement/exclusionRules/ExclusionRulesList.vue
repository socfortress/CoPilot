<template>
	<div class="sigma-queries-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total :
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>

				<NewExclusionRuleButton v-if="showCreationButton" @success="getData()" />
			</div>
			<n-checkbox v-model:checked="filters.enabledOnly">Enabled only</n-checkbox>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
		</div>

		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="list.length">
					<ExclusionRuleItem
						v-for="item of list"
						:key="item.id"
						:entity="item"
						class="item-appear item-appear-bottom item-appear-005"
						@deleted="getData()"
						@updated="getData()"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>

		<div class="footer flex justify-end">
			<n-pagination
				v-if="list.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ExclusionRulesQuery } from "@/api/endpoints/incidentManagement/exclusionRules"
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import { NButton, NCheckbox, NEmpty, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import ExclusionRuleItem from "./ExclusionRuleItem.vue"
import NewExclusionRuleButton from "./NewExclusionRuleButton.vue"

const { showCreationButton = true } = defineProps<{ showCreationButton?: boolean }>()

const emit = defineEmits<{
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
	(e: "loaded", value: number): void
}>()

const InfoIcon = "carbon:information"
const message = useMessage()
const filters = ref({ enabledOnly: false })
const loading = ref(false)
const list = ref<ExclusionRule[]>([])
const total = ref(0)

const currentPage = ref(1)
const pageSizes = [10, 25, 50, 100]
const pageSize = ref(pageSizes[1])
const header = ref()
const pageSlot = ref(8)
const simpleMode = ref(false)
const showSizePicker = ref(true)

function getData() {
	loading.value = true

	const query: Partial<ExclusionRulesQuery> = {
		pagination: {
			limit: pageSize.value,
			skip: (currentPage.value - 1) * pageSize.value
		}
	}

	if (filters.value.enabledOnly) {
		query.filters = { enabledOnly: filters.value.enabledOnly }
	}

	Api.incidentManagement.exclusionRules
		.getExclusionRulesList(query)
		.then(res => {
			if (res.data.success) {
				list.value = res.data.exclusions || []
				total.value = res.data.pagination.total || 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
			emit("loaded", total.value)
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

watch(pageSize, () => {
	currentPage.value = 1
})

watch([currentPage, pageSize, () => filters.value.enabledOnly], () => {
	getData()
})

onBeforeMount(() => {
	getData()

	emit("mounted", {
		reload: getData
	})
})
</script>
