<template>
	<div class="services-list">
		<div class="header mb-4 flex gap-2 justify-between items-center" v-if="!hideTotals">
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
						@click="setItem(item)"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { toRefs, computed } from "vue"
import { NSpin, NEmpty } from "naive-ui"
import ServiceItem from "./Item.vue"
import type { ServiceItemData, ServiceItemType } from "./types"

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
