<template>
	<component :is="componentName" v-bind="options">
		<template v-if="$slots.default">
			<slot />
		</template>
		<template v-else>
			<Icon v-if="icon" :icon :width="options.size || undefined" :height="options.size || undefined" />
		</template>
	</component>
</template>

<script setup lang="ts">
import type { IconifyIcon } from "@iconify/vue"
import { Icon, loadIcon } from "@iconify/vue"
import { NIcon, NIconWrapper } from "naive-ui"
import { computed, ref, watchEffect } from "vue"

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

const load = (name: string) => loadIcon(name).catch(() => console.error(`Failed to load icon ${name}`))

const icon = ref<void | Required<IconifyIcon>>()

// Icons not used before are fetched from the Iconify API, so loads finish in any order.
// Only the icon still asked for may be shown: a slow load for a name that has since
// changed must not land on top of the current one (#1217: a spinner fetched for the
// first time arrived after the save it stood for, and stayed on screen for good).
watchEffect(() => {
	const name = props.name
	if (!name) {
		icon.value = undefined
		return
	}
	load(name).then(res => {
		if (props.name === name) icon.value = res
	})
})
</script>
