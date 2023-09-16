<template>
	<div class="main">
		<n-scrollbar ref="scrollbar">
			<div class="view" :class="[{ boxed }, `route-${routeName}`]">
				<slot></slot>
			</div>
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import { computed, ref, onMounted } from "vue"
import { NScrollbar } from "naive-ui"
import { useRoute, useRouter } from "vue-router"
import { useThemeStore } from "@/stores/theme"

defineOptions({
	name: "MainContainer"
})

const router = useRouter()
const route = useRoute()
const routeName = computed<string>(() => route.name?.toString() || "")
const boxed = computed(() => useThemeStore().isBoxed)
const scrollbar = ref()

onMounted(() => {
	router.afterEach(() => {
		if (scrollbar?.value?.scrollTo) {
			scrollbar?.value.scrollTo({ top: 0 })
		}
	})
})
</script>

<style lang="scss" scoped>
.main {
	width: 100%;
	position: relative;
	background-color: var(--bg-body);

	/*
	.view {
		padding: var(--view-padding);

		&.boxed {
			max-width: var(--boxed-width);
			margin: 0 auto;
		}
	}
	*/
}
</style>
