<template>
	<n-config-provider :theme="theme" :theme-overrides="themeOverrides" preflight-style-disabled>
		<n-loading-bar-provider :container-style="{ height: '3px' }">
			<n-message-provider>
				<n-notification-provider>
					<n-dialog-provider>
						<slot />
					</n-dialog-provider>
				</n-notification-provider>
			</n-message-provider>
		</n-loading-bar-provider>
		<n-global-style />
	</n-config-provider>
</template>

<script lang="ts" setup>
import {
	NGlobalStyle,
	NConfigProvider,
	NDialogProvider,
	NMessageProvider,
	NNotificationProvider,
	NLoadingBarProvider,
	type GlobalThemeOverrides
} from "naive-ui"
import { useThemeStore } from "@/stores/theme"
import { useWindowSize } from "@vueuse/core"
import { computed, onBeforeMount, watch } from "vue"

const { width } = useWindowSize()

const theme = computed(() => useThemeStore().naiveTheme)
const themeOverrides = computed<GlobalThemeOverrides>(() => useThemeStore().themeOverrides)
const style = computed<CSSStyleDeclaration>(() => useThemeStore().style)

watch(style, () => {
	setGlobalVars()
})
watch(width, () => {
	useThemeStore().updateVars()
})

function setGlobalVars() {
	const html = document.children[0] as HTMLElement
	const { style: htmlStyle } = html
	for (const key in style.value) {
		htmlStyle.setProperty(key, style.value[key])
	}
}

onBeforeMount(() => {
	useThemeStore().updateVars()
	setGlobalVars()
})
</script>
