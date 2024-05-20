<template>
	<n-config-provider :theme="theme" :theme-overrides="themeOverrides" preflight-style-disabled>
		<n-loading-bar-provider :container-style="{ height: '3px' }">
			<n-message-provider>
				<n-notification-provider>
					<n-dialog-provider>
						<GlobalListener>
							<slot />
						</GlobalListener>
					</n-dialog-provider>
				</n-notification-provider>
			</n-message-provider>
		</n-loading-bar-provider>
		<n-global-style />
	</n-config-provider>
</template>

<script lang="ts" setup>
import { computed,  watch } from "vue"
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
import GlobalListener from "@/layouts/common/GlobalListener.vue"
import type { ThemeName } from "@/types/theme.d"

const { width } = useWindowSize()

const themeStore = useThemeStore()

const theme = computed(() => themeStore.naiveTheme)
const themeOverrides = computed<GlobalThemeOverrides>(() => themeStore.themeOverrides)
const style = computed<CSSStyleDeclaration>(() => themeStore.style)
const themeName = computed<ThemeName>(() => themeStore.themeName)

watch(
	style,
	() => {
		setGlobalVars()
	},
	{ immediate: true }
)
watch(
	themeName,
	(val, old) => {
		setThemeName(val, old)
	},
	{ immediate: true }
)
watch(
	width,
	() => {
		themeStore.updateVars()
	},
	{ immediate: true }
)

function setGlobalVars() {
	const html = document.children[0] as HTMLElement
	const { style: htmlStyle } = html
	for (const key in style.value) {
		htmlStyle.setProperty(key, style.value[key])
	}
}

function setThemeName(val: ThemeName, old?: ThemeName) {
	const html = document.children[0] as HTMLElement
	if (old) {
		html.classList.remove(`theme-${old}`)
	}
	html.classList.add(`theme-${val}`)
}
</script>
