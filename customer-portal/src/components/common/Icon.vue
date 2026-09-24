<template>
	<component :is="componentName" v-bind="options">
		<template v-if="$slots.default">
			<slot />
		</template>
		<template v-else>
			<Icon v-if="name" :icon="name" :width="options.size || undefined" :height="options.size || undefined" />
		</template>
	</component>
</template>

<script setup lang="ts">
// The offline build renders only the collections bundled in main.ts and never calls the Iconify API.
import { Icon } from "@iconify/vue/offline"
import { NIcon, NIconWrapper } from "naive-ui"
import { computed } from "vue"

const props = defineProps<{
	name?: string
	size?: number
	bgSize?: number
	color?: string
	bgColor?: string
	borderRadius?: number
	depth?: 1 | 2 | 3 | 4 | 5
}>()

const useWrapper = computed(() => !!(props.bgColor || props.bgSize || props.borderRadius))
const componentName = computed(() => (useWrapper.value ? NIconWrapper : NIcon))

const options = computed(() => {
	const opt: Partial<{ size: number; color: string; borderRadius: number; iconColor: string; depth: number }> = {}
	if (useWrapper.value) {
		if (props.bgSize !== undefined) opt.size = props.bgSize
		if (props.bgColor !== undefined) opt.color = props.bgColor
		if (props.borderRadius !== undefined) opt.borderRadius = props.borderRadius
		if (props.color !== undefined) opt.iconColor = props.color
	} else {
		if (props.color !== undefined) opt.color = props.color
		if (props.depth !== undefined) opt.depth = props.depth
		if (props.size !== undefined) opt.size = props.size
	}
	return opt
})
</script>
