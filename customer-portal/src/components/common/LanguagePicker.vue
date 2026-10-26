<template>
	<n-select
		:value="localesStore.locale"
		:options
		:loading="localesStore.saving"
		:disabled="!localesStore.canChoose || localesStore.saving"
		:consistent-menu-width="false"
		data-testid="language-picker"
		@update:value="(value: LocaleCodes) => choose(value)"
	/>
</template>

<script setup lang="ts">
import type { LocaleCodes } from "@/lang/config"
import { NSelect, useMessage } from "naive-ui"
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import { LOCALE_NAMES } from "@/lang/config"
import { useLocalesStore } from "@/stores/i18n"

/**
 * The portal's language (#1310): the languages the user's customers offer, each in its own name,
 * saved on their account at once (no Save button: the page changes language as they pick).
 */
const localesStore = useLocalesStore()
const message = useMessage()
const { t } = useI18n()

const options = computed(() => localesStore.available.map(code => ({ label: LOCALE_NAMES[code], value: code })))

async function choose(locale: LocaleCodes) {
	try {
		await localesStore.choose(locale)
		message.success(t("common.language.saved"))
	} catch {
		message.error(t("common.language.failed"))
	}
}
</script>
