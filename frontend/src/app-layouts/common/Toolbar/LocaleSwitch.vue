<template>
	<n-popselect v-model:value="currentLocale" :options="list" :render-label="renderLabel">
		<Icon :size="19" :name="MultiLanguageIcon" />
	</n-popselect>
</template>

<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
import { useLocalesStore } from "@/stores/i18n"
import { NPopselect, type SelectOption } from "naive-ui"
import { computed, h, type VNodeChild } from "vue"

const MultiLanguageIcon = "ion:language-outline"

const localesStore = useLocalesStore()

const { setLocale, t } = localesStore

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
				default: () => {
					switch (option.label) {
						case "it":
							return t("italian")
						case "en":
							return t("english")
						case "es":
							return t("spanish")
						case "fr":
							return t("french")
						case "de":
							return t("german")
						case "jp":
							return t("japanese")
						default:
							return option.label
					}
				}
			}
		)
	]
}
</script>
