<template>
	<n-config-provider :rtl="rtlOptions" :theme="theme" :theme-overrides="themeOverrides" preflight-style-disabled>
		<n-loading-bar-provider container-class="h-0.75">
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
import { computed, watch } from "vue"
import GlobalListener from "@/layouts/common/GlobalListener.vue"
import type { RtlItem } from "naive-ui/es/config-provider/src/internal-interface"
import { rtlStyles } from "./rtlProvider"
import type { ThemeName } from "@/types/theme.d"

const { width } = useWindowSize()
const themeStore = useThemeStore()
const theme = computed(() => themeStore.naiveTheme)
const themeName = computed<ThemeName>(() => themeStore.themeName)
const themeOverrides = computed<GlobalThemeOverrides>(() => themeStore.themeOverrides)
const style = computed(() => themeStore.style)
const isRTL = computed(() => themeStore.isRTL)
const rtlOptions = computed<RtlItem[] | undefined>(() => (isRTL.value ? rtlStyles : undefined))

watch(
	[isRTL, style],
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

// This function allows you to utilize the values in the style object as variables within your CSS/SCSS code like: var(-–bg-color)
function setGlobalVars() {
	const html = document.children[0] as HTMLElement
	const body = document.getElementsByTagName("body")?.[0]
	if (isRTL.value && body) {
		body.classList.add("direction-rtl")
		body.classList.remove("direction-ltr")
	} else {
		body.classList.remove("direction-rtl")
		body.classList.add("direction-ltr")
	}
	//html.dir = isRTL.value ? "rtl" : "ltr"
	const { style: htmlStyle } = html
	for (const key in style.value) {
		htmlStyle.setProperty("--" + key, style.value[key])
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
