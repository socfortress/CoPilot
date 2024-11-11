<template>
	<div class="icon" :class="{ boxed }" :style="`--size:${boxSize}px`">
		<div v-if="boxed" class="bg"></div>
		<Icon v-if="$slots.default" :size="iconFinalSize">
			<slot></slot>
		</Icon>
		<Icon v-else :size="iconFinalSize" :name="iconName"></Icon>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { computed } from "vue"

const {
	boxSize = 40,
	iconSize = 28,
	boxed = false,
	iconName,
	color
} = defineProps<{
	boxSize?: number
	iconSize?: number
	iconName?: string
	boxed?: boolean
	color?: string
}>()

const style = computed(() => useThemeStore().style)

const iconColor = computed(() => color || style.value["primary-color"])
const iconBoxedSize = computed(() => (boxSize / 100) * 45)
const iconFinalSize = computed(() => (boxed ? iconBoxedSize.value : iconSize))
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
