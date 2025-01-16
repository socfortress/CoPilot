<template>
	<div id="app-main" class="main">
		<n-scrollbar ref="scrollbar">
			<div
				id="app-view"
				class="view"
				:class="{ boxed, 'view-padded': overridePadded === true, 'view-no-padded': overridePadded === false }"
			>
				<slot />
			</div>
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { NScrollbar } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import { type RouteLocationNormalizedGeneric, useRoute, useRouter } from "vue-router"

const themeStore = useThemeStore()
const router = useRouter()
const route = useRoute()
const themeBoxed = computed<boolean>(() => themeStore.isBoxed)
const overrideBoxed = ref<boolean | undefined>(undefined)
const overridePadded = ref<boolean | undefined>(undefined)
const boxed = computed<boolean>(() => (overrideBoxed.value !== undefined ? overrideBoxed.value : themeBoxed.value))
const scrollbar = ref()

function checkThemeOverrides(currentRoute: RouteLocationNormalizedGeneric) {
	if (currentRoute.meta?.theme?.boxed?.enabled !== undefined) {
		overrideBoxed.value = currentRoute.meta.theme.boxed.enabled
	} else {
		overrideBoxed.value = undefined
	}

	if (currentRoute.meta?.theme?.padded?.enabled !== undefined) {
		overridePadded.value = currentRoute.meta.theme.padded.enabled
	} else {
		overridePadded.value = undefined
	}
}

router.beforeEach(checkThemeOverrides)

onMounted(() => {
	checkThemeOverrides(route)

	router.afterEach(() => {
		if (scrollbar?.value?.scrollTo) {
			scrollbar?.value.scrollTo({ top: 0, behavior: "smooth" })
		}
	})
})
</script>

<style lang="scss" scoped>
.main {
	width: 100%;
	position: relative;
	background-color: var(--bg-body-color);

	.view {
		padding: 0 var(--view-padding);
		flex-grow: 1;
		width: 100%;
		margin: 0 auto;

		&.boxed {
			max-width: var(--boxed-width);
		}
		&.view-no-padded {
			padding: 0;
		}
	}
}
</style>
