<template>
	<component :is="componentName" v-bind="options">
		<template v-if="$slots.default">
			<slot />
		</template>
		<template v-else>
			<Icon v-if="icon" :icon="icon" :width="size" :height="size" />
		</template>
	</component>
</template>

<script setup lang="ts">
import { NIconWrapper, NIcon } from "naive-ui"
import { Icon, loadIcon, type IconifyIcon } from "@iconify/vue"
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
	const opt: any = {}
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

function setIcon(name: string | undefined) {
	if (name) {
		load(name).then(res => (icon.value = res))
	}
}

setIcon(props.name)

watchEffect(() => setIcon(props.name))
</script>
