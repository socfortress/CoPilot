<template>
	<n-card :title segmented class="@container" :size>
		<div class="my-1 grid grid-cols-1 gap-4 @md:grid-cols-2 @xl:grid-cols-3 @3xl:grid-cols-4">
			<slot name="prefix" />
			<CardKV
				v-for="(field, index) in fields"
				:key="field.key || field.label || index"
				:label="field.label || field.key || index"
				:value="getFieldValue(field)"
			/>
			<slot name="suffix" />
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { CardProps } from "naive-ui"
import type { SafeAny } from "@/types/utils"
import { NCard } from "naive-ui"
import CardKV from "@/components/common/cards/CardKV.vue"

export interface Field {
	label?: string
	key?: string | number
	value?: SafeAny
	formatter?: (value: any) => string | null
}

const { fields } = defineProps<{ fields: Field[]; title?: string; size?: CardProps["size"] }>()

function getFieldValue(field: Field): string {
	const value = field.value

	if (field.formatter) {
		return field.formatter(value) || "—"
	}

	if (value === undefined) {
		return "—"
	}

	if (typeof value === "string") {
		return value.trim() || "—"
	}

	return String(value)
}
</script>
