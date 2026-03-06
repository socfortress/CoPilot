<template>
	<n-card size="small" content-class="divide-border flex flex-col divide-y px-3.5! py-1!" :embedded :title :segmented>
		<div v-for="(value, key) of list" :key class="group/prop-item flex items-center justify-between gap-4 py-2">
			<div class="text-secondary text-sm whitespace-nowrap">{{ key }}</div>
			<div class="group-hover/prop-item:text-primary text-right font-mono text-sm">
				{{ stringFormat(key, value) }}
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { isDate } from "@/utils"
import { formatDate } from "@/utils/format"

export type TransformerValue = string | Date | number | null | object
export type Transformer = (val?: TransformerValue) => TransformerValue

const { list, embedded, dateAutodetect, transformer, title, segmented } = defineProps<{
	list: object
	embedded?: boolean
	dateAutodetect?: boolean
	transformer?: Record<"all" | string, Transformer>
	title?: string
	segmented?: boolean
}>()

const dFormats = useSettingsStore().dateFormat

function stringFormat(key: string, val?: string | Date | number | null) {
	if (transformer?.[key]) {
		return transformer[key](val)
	}

	if (dateAutodetect && isDate(val)) {
		return formatDate(val as string, dFormats.datetimesec)
	}

	if (transformer?.all) {
		return transformer.all(val)
	}

	return JSON.stringify(val)
}
</script>
