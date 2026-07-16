<template>
	<div ref="sidebarRef" class="shrink-0 basis-1/3 md:max-w-70">
		<div ref="sidebarCardRef" class="flex flex-col gap-2 will-change-transform">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
import { useElementBounding, useRafFn } from "@vueuse/core"
import { useMotionProperties } from "@vueuse/motion"
import { ref, watch } from "vue"

const sidebarRef = ref(null)
const sidebarCardRef = ref(null)
const { top: sidebarTop } = useElementBounding(sidebarRef)
const { transform: styleCardTransform } = useMotionProperties(sidebarCardRef)

const { resume } = useRafFn(
	() => {
		const targetY = sidebarTop.value <= 50 ? sidebarTop.value * -1 + 50 : 0
		styleCardTransform.translateY = `${targetY}px`
	},
	{ immediate: false }
)

watch(sidebarTop, () => {
	resume()
})
</script>
