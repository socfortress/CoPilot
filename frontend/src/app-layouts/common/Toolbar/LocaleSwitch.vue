<template>
	<n-popselect v-model:value="currentLocale" :options="list" :render-label="renderLabel">
		<Icon :size="19" :name="MultiLanguageIcon" />
	</n-popselect>
</template>

<script lang="ts" setup>
import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useLocalesStore } from "@/stores/i18n"
import { NPopselect } from "naive-ui"
import { computed, h } from "vue"
import { useI18n } from "vue-i18n"

const MultiLanguageIcon = "ion:language-outline"
const localesStore = useLocalesStore()
const { setLocale } = localesStore
const { t } = useI18n()

const list = computed(() =>
	localesStore.availableLocales.map(i => ({
		label: i,
		value: i
	}))
)

const currentLocale = computed({
	get: () => localesStore.locale,
	set: v => setLocale(v)
})

function renderLabel(option: SelectOption): VNodeChild {
	return [
		h(Icon, {
			color: "#000",
			style: {
				verticalAlign: "-0.15em",
				marginRight: "8px"
			},
			name: `circle-flags:${option.label}`
		}),
		h(
			"span",
			{},
			{
				default: () => t(`locales.${option.label}`, `${option.label}`)
			}
		)
	]
}
</script>
