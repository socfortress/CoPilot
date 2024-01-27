<template>
	<div class="pagination-indeterminate flex items-center gap-2">
		<n-input-number
			size="small"
			v-model:value="page"
			:min="1"
			button-placement="both"
			class="page"
			:disabled="disabled"
		>
			<template #minus-icon>
				<Icon :name="ArrowBackIcon"></Icon>
			</template>
			<template #add-icon>
				<Icon :name="ArrowForwardIcon"></Icon>
			</template>
		</n-input-number>
		<n-select
			size="small"
			v-if="showPageSizes"
			v-model:value="pageSize"
			:options="pageSizesOptions"
			:show-checkmark="false"
			class="page-sizes"
			:disabled="disabled"
		/>
		<n-select
			size="small"
			v-if="showSort"
			v-model:value="sort"
			:options="sortOptions"
			:show-checkmark="false"
			class="sort"
			:disabled="disabled"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { NSelect, NInputNumber } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { watch } from "vue"

const page = defineModel<number>("page", { default: 1 })
const pageSize = defineModel<number>("pageSize", { default: 10 })
const sort = defineModel<"asc" | "desc">("sort", { default: "desc" })

const props = defineProps<{ showPageSizes?: boolean; showSort?: boolean; pageSizes?: number[]; disabled?: boolean }>()
const { pageSizes, disabled, showPageSizes, showSort } = toRefs(props)

const pageSizesOptions = computed(() =>
	(pageSizes.value || [10, 25, 50, 100]).map(o => ({ label: o + " / page", value: o }))
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
