<template>
	<n-popselect v-model:value="currentLocale" :options="list" :render-label="renderLabel">
		<Icon :size="19" :name="MultiLanguageIcon"></Icon>
	</n-popselect>
</template>

<script lang="ts" setup>
import { NPopselect, type SelectOption } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useStoreI18n } from "@/composables/useStoreI18n"
import { computed, h, type VNodeChild } from "vue"

const MultiLanguageIcon = "ion:language-outline"

const { getAvailableLocales, getLocale, setLocale, t } = useStoreI18n()

const list = computed(() =>
	getAvailableLocales().map(i => ({
		label: i,
		value: i
	}))
)

const currentLocale = computed({
	get: () => getLocale(),
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
					if (option.label === "it") return t("italian")
					if (option.label === "en") return t("english")
					if (option.label === "es") return t("spanish")
					if (option.label === "fr") return t("french")
					if (option.label === "de") return t("german")
					if (option.label === "jp") return t("japanese")
				}
			}
		)
	]
}
</script>
