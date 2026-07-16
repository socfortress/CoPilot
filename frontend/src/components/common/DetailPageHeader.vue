<template>
	<div class="detail-page-header flex min-w-0 flex-wrap gap-x-4 gap-y-2">
		<n-button quaternary class="shrink-0" @click="onBack()">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			{{ backLabel }}
		</n-button>

		<div v-if="hasTitleArea" class="mt-0.5 flex min-w-80 flex-1 flex-wrap items-baseline gap-x-2 gap-y-0.5">
			<slot name="title">
				<span v-if="title" class="truncate text-lg font-semibold" :title>{{ title }}</span>
			</slot>
			<div v-if="slots.meta" class="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-0.5">
				<slot name="meta" />
			</div>
		</div>

		<div v-if="slots.actions" class="ml-auto flex shrink-0 flex-wrap items-center justify-end gap-2">
			<slot name="actions" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { EntityRoute } from "@/composables/useNavigation"
import { NButton } from "naive-ui"
import { computed, useSlots } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const {
	title,
	backRoute,
	backLabel = "Back"
} = defineProps<{
	/** Main heading — usually the entity name (fallback to its id while loading). */
	title?: string
	/** Where "Back" lands on a cold load / deep link (falls back after history.back). */
	backRoute?: EntityRoute
	backLabel?: string
}>()

const slots = useSlots()
const { goBack } = useNavigation()

const BackIcon = "carbon:arrow-left"

const hasTitleArea = computed(() => !!title || !!slots.title || !!slots.meta)

function onBack() {
	goBack(backRoute)
}
</script>
