<template>
	<div class="icon" :class="{ boxed }" :style="`--size:${boxSize}px`">
		<div class="bg" v-if="boxed"></div>
		<Icon :size="iconFinalSize" v-if="$slots.default">
			<slot></slot>
		</Icon>
		<Icon :size="iconFinalSize" :name="iconName" v-else></Icon>
	</div>
</template>

<script setup lang="ts">
import { toRefs, computed } from "vue"
import { useThemeStore } from "@/stores/theme"
import Icon from "@/components/common/Icon.vue"

const props = withDefaults(
	defineProps<{
		boxSize?: number
		iconSize?: number
		iconName?: string
		boxed?: boolean
		color?: string
	}>(),
	{ boxSize: 40, iconSize: 28, boxed: false }
)
const { boxed, boxSize, iconSize, color } = toRefs(props)

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)

const iconColor = computed(() => color?.value || style.value["--primary-color"])
const iconBoxedSize = computed(() => (boxSize.value / 100) * 45)
const iconFinalSize = computed(() => (boxed?.value ? iconBoxedSize.value : iconSize.value))
</script>

<style scoped lang="scss">
.icon {
	color: v-bind(iconColor);
	width: var(--size);
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;

	&.boxed {
		height: var(--size);

		.bg {
			background-color: v-bind(iconColor);
			opacity: 0.1;
			position: absolute;
			top: 0;
			left: 0;
			border-radius: 50%;
			width: 100%;
			height: 100%;
		}
	}
}
</style>
