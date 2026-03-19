<template>
	<CardEntity hoverable clickable size="small" :class="{ highlighted: selected }" @click="$emit('select')">
		<template #headerMain>
			<div class="flex items-center gap-2">
				<div class="flex h-full items-center justify-center" :style="{ color: category.color }">
					<Icon :name="getDashboardIcon(category.icon)" :size="16" />
				</div>
				{{ category.title }}
			</div>
		</template>
		<template #default>
			<div class="flex flex-col gap-2">
				<p class="text-xs">
					{{ category.description }}
				</p>
				<div v-if="category.tags.length" class="text-tertiary flex flex-wrap gap-2 text-xs">
					<span v-for="tag in category.tags" :key="tag">#{{ tag }}</span>
				</div>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap gap-2">
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
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardCategory } from "@/types/dashboards.d"
import { NTag } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getDashboardIcon } from "./utils"

defineProps<{
	category: DashboardCategory
	selected?: boolean
}>()

defineEmits<{
	select: []
}>()
</script>
