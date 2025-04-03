<template>
	<n-config-provider
		:rtl="rtlOptions"
		:theme
		:theme-overrides
		:locale="providerLocale"
		:date-locale="providerDateLocale"
		preflight-style-disabled
		inline-theme-disabled
	>
		<n-loading-bar-provider container-class="h-0.75!">
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
import type { GlobalThemeOverrides } from "naive-ui"
import type { RtlItem } from "naive-ui/es/config-provider/src/internal-interface"
import GlobalListener from "@/app-layouts/common/GlobalListener.vue"
import { useLocalesStore } from "@/stores/i18n"
import { useThemeStore } from "@/stores/theme"
import {
	NConfigProvider,
	NDialogProvider,
	NGlobalStyle,
	NLoadingBarProvider,
	NMessageProvider,
	NNotificationProvider
} from "naive-ui"
import { computed, onBeforeMount } from "vue"
import { rtlStyles } from "./rtlProvider"

const localesStore = useLocalesStore()
const themeStore = useThemeStore()
const theme = computed(() => themeStore.naiveTheme)
const themeOverrides = computed<GlobalThemeOverrides>(() => themeStore.themeOverrides)
const isRTL = computed(() => themeStore.isRTL)
const rtlOptions = computed<RtlItem[] | undefined>(() => (isRTL.value ? rtlStyles : undefined))
const providerLocale = computed(() => localesStore.naiveuiLocale)
const providerDateLocale = computed(() => localesStore.naiveuiDateLocale)

onBeforeMount(() => {
	themeStore.initTheme()
})
</script>
