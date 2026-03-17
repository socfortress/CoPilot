<template>
	<CardEntity hoverable>
		<template #headerMain>
			<span class="font-semibold">{{ template.title }}</span>
		</template>

		<div class="px-4 py-2 text-sm opacity-80">
			{{ template.description }}
		</div>

		<template #footerMain>
			<Badge type="splitted">
				<template #label>Panels</template>
				<template #value>{{ template.panels.length }}</template>
			</Badge>
		</template>

		<template #footerExtra>
			<n-button
				v-if="!isEnabled"
				size="small"
				type="primary"
				:disabled="!canEnable"
				@click="$emit('enable', template)"
			>
				<template #icon>
					<Icon :name="EnableIcon" :size="14" />
				</template>
				Enable
			</n-button>
			<n-button v-else size="small" type="error" quaternary @click="$emit('disable', template)">
				<template #icon>
					<Icon :name="DisableIcon" :size="14" />
				</template>
				Disable
			</n-button>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardTemplate } from "@/types/dashboards.d"
import { NButton } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	template: DashboardTemplate
	isEnabled: boolean
	canEnable: boolean
}>()

defineEmits<{
	enable: [template: DashboardTemplate]
	disable: [template: DashboardTemplate]
}>()

const EnableIcon = "carbon:add-alt"
const DisableIcon = "carbon:subtract-alt"
</script>
