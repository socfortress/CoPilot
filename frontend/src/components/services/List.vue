<template>
	<div class="services-list">
		<div v-if="!hideTotals" class="header mb-4 flex items-center justify-between gap-2">
			<div>
				Total:
				<strong class="font-mono">{{ total }}</strong>
			</div>
		</div>
		<n-spin :show="loading">
			<div class="list">
				<template v-if="list.length">
					<ServiceItem
						v-for="item of list"
						:key="item.id"
						:type="type"
						:data="item"
						:embedded="embedded"
						:selectable="isSelectable(item)"
						:disabled="isDisabled(item)"
						:checked="selected?.id === item.id"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
						@click="setItem(item)"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ServiceItemData, ServiceItemType } from "./types"
import { NEmpty, NSpin } from "naive-ui"
import { computed, toRefs } from "vue"
import ServiceItem from "./Item.vue"

const props = defineProps<{
	type: ServiceItemType
	list: ServiceItemData[]
	embedded?: boolean
	loading?: boolean
	hideTotals?: boolean
	selectable?: boolean
	disabledIdsList?: (string | number)[]
}>()
const { type, list, embedded, hideTotals, selectable, disabledIdsList } = toRefs(props)

const selected = defineModel<ServiceItemData | null>("selected", { default: null })

const total = computed<number>(() => {
	return list.value.length || 0
})

function isDisabled(item: ServiceItemData) {
	return (disabledIdsList.value || []).includes(item.id)
}

function isSelectable(item: ServiceItemData) {
	return selectable.value && !isDisabled(item)
}

function setItem(item: ServiceItemData) {
	if (!isDisabled(item)) {
		selected.value = selected.value?.id === item.id ? null : item
	}
}
</script>

<style lang="scss" scoped>
.services-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
