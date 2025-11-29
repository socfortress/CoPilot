<template>
	<div class="pagination-indeterminate flex items-center gap-2">
		<n-input-number
			v-model:value="page"
			size="small"
			:min="1"
			button-placement="both"
			class="page"
			:disabled="disabled"
		>
			<template #minus-icon>
				<Icon :name="ArrowBackIcon" />
			</template>
			<template #add-icon>
				<Icon :name="ArrowForwardIcon" />
			</template>
		</n-input-number>
		<n-select
			v-if="showPageSizes"
			v-model:value="pageSize"
			size="small"
			:options="pageSizesOptions"
			:show-checkmark="false"
			class="page-sizes"
			:disabled="disabled"
		/>
		<n-select
			v-if="showSort"
			v-model:value="sort"
			size="small"
			:options="sortOptions"
			:show-checkmark="false"
			class="sort"
			:disabled="disabled"
		/>
	</div>
</template>

<script setup lang="ts">
import { NInputNumber, NSelect } from "naive-ui"
import { computed, toRefs, watch } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ showPageSizes?: boolean; showSort?: boolean; pageSizes?: number[]; disabled?: boolean }>()
const page = defineModel<number>("page", { default: 1 })
const pageSize = defineModel<number>("pageSize", { default: 10 })
const sort = defineModel<"asc" | "desc">("sort", { default: "desc" })

const { pageSizes, disabled, showPageSizes, showSort } = toRefs(props)

const pageSizesOptions = computed(() =>
	(pageSizes.value || [10, 25, 50, 100]).map(o => ({ label: `${o} / page`, value: o }))
)

const sortOptions = [
	{ label: "Desc", value: "desc" },
	{ label: "Asc", value: "asc" }
]

const ArrowForwardIcon = "ion:chevron-forward"
const ArrowBackIcon = "ion:chevron-back"

watch(page, val => {
	if (!val) {
		page.value = 1
	}
})
</script>

<style lang="scss" scoped>
.pagination-indeterminate {
	.page {
		width: 90px;
		text-align: center;
	}
	.page-sizes {
		width: auto;
	}
	.sort {
		width: auto;
	}
}
</style>
