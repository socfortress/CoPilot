<template>
	<CardEntity hoverable clickable :class="{ highlighted: selected }" @click="$emit('select')">
		<template #headerMain>
			<div class="flex items-center gap-2">
				<Icon :name="iconName" :size="20" :style="{ color: category.color }" />
				<span class="font-bold">{{ category.title }}</span>
			</div>
		</template>

		<div class="px-4 py-2 text-sm opacity-80">
			{{ category.description }}
		</div>

		<template #footerMain>
			<div class="flex flex-wrap gap-1">
				<Badge type="splitted">
					<template #label>Vendor</template>
					<template #value>{{ category.vendor }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Type</template>
					<template #value>{{ category.event_type }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex flex-wrap gap-1">
				<n-tag v-for="tag in category.tags.slice(0, 4)" :key="tag" size="tiny" :bordered="false">
					{{ tag }}
				</n-tag>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardCategory } from "@/types/dashboards.d"
import { NTag } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	category: DashboardCategory
	selected?: boolean
}>()

defineEmits<{
	select: []
}>()

const iconName = "carbon:dashboard"
</script>
