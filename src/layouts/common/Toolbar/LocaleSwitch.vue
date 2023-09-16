<template>
	<n-popselect v-model:value="currentLocale" :options="list" :render-label="renderLabel">
		<n-icon size="19">
			<MultiLanguageIcon />
		</n-icon>
	</n-popselect>
</template>

<script lang="ts" setup>
import { NIcon, NPopselect, type SelectOption } from "naive-ui"
import MultiLanguageIcon from "@vicons/ionicons5/LanguageOutline"
import it from "flag-icons/flags/4x3/it.svg"
import en from "flag-icons/flags/4x3/us.svg"
import fr from "flag-icons/flags/4x3/fr.svg"
import es from "flag-icons/flags/4x3/es.svg"
import de from "flag-icons/flags/4x3/de.svg"
import jp from "flag-icons/flags/4x3/jp.svg"
import { getAvailableLocales, getLocale, setLocale } from "@/utils/i18n"
import { computed, h, type VNodeChild } from "vue"
import { useI18n } from "vue-i18n"

defineOptions({
	name: "LocaleSwitch"
})

const { t } = useI18n()

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
		h(
			NIcon,
			{
				color: "#000",
				style: {
					verticalAlign: "-0.15em",
					marginRight: "8px"
				}
			},
			{
				default: () => {
					if (option.label === "it") return h(it)
					if (option.label === "en") return h(en)
					if (option.label === "es") return h(es)
					if (option.label === "fr") return h(fr)
					if (option.label === "de") return h(de)
					if (option.label === "jp") return h(jp)
				}
			}
		),
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
