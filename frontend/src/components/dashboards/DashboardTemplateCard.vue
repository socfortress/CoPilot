<template>
	<CardEntity hoverable size="small">
		<template #headerMain>
			{{ template.title }}
		</template>
		<template #default>
			<p class="text-xs">
				{{ template.description }}
			</p>
		</template>

		<template #footerMain>
			<Badge type="splitted">
				<template #label>Panels</template>
				<template #value>{{ template.panels.length }}</template>
			</Badge>
		</template>

		<template #footerExtra>
			<n-tooltip v-if="!isEnabled" :disabled="!disabledTooltipText" class="px-2! py-1!">
				<template #trigger>
					<n-button size="small" type="primary" :disabled="!canEnable" @click="$emit('enable', template)">
						<template #icon>
							<Icon :name="disabledTooltipText ? LockedIcon : EnableIcon" />
						</template>
						Enable
					</n-button>
				</template>
				<div class="text-sm">
					{{ disabledTooltipText }}
				</div>
			</n-tooltip>
			<n-button v-else size="small" type="error" quaternary @click="$emit('disable', template)">
				<template #icon>
					<Icon :name="DisableIcon" />
				</template>
				Disable
			</n-button>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { DashboardTemplate } from "@/types/dashboards.d"
import { NButton, NTooltip } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	template: DashboardTemplate
	isEnabled: boolean
	canEnable: boolean
	disabledTooltipText?: string
}>()

defineEmits<{
	enable: [template: DashboardTemplate]
	disable: [template: DashboardTemplate]
}>()

const EnableIcon = "carbon:add-alt"
const DisableIcon = "carbon:subtract-alt"
const LockedIcon = "carbon:locked"
</script>
