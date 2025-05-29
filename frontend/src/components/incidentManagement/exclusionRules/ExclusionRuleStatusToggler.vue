<template>
	<n-switch
		v-model:value="entity.enabled"
		:rail-style
		:loading="updatingStatus"
		@update:value="toggleExclusionRuleStatus()"
	>
		<template #checked>Enabled</template>
		<template #unchecked>Disabled</template>
	</n-switch>
</template>

<script setup lang="ts">
import type { CSSProperties } from "vue"
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules.d"
import { NSwitch, useMessage } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { useThemeStore } from "@/stores/theme"

const props = defineProps<{
	entity: ExclusionRule
}>()

const emit = defineEmits<{
	(e: "loading", value: boolean): void
	(e: "updated", value: ExclusionRule): void
}>()

const { entity } = toRefs(props)

const message = useMessage()
const themeStore = useThemeStore()
const checkedColor = computed(() => themeStore.style["success-color-rgb"])
const uncheckedColor = computed(() => themeStore.style["border-color-rgb"])
const updatingStatus = ref(false)

function railStyle({ focused, checked }: { focused: boolean; checked: boolean }) {
	const style: CSSProperties = {}
	if (checked) {
		style.background = `rgb(${checkedColor.value} / 40%)`
		if (focused) {
			style.boxShadow = `0 0 0 2px rgb(${checkedColor.value} / 30%)`
		}
	} else {
		style.background = `rgb(${uncheckedColor.value})`
		if (focused) {
			style.boxShadow = `0 0 0 2px rgb(${uncheckedColor.value} / 10%)`
		}
	}
	return style
}

function toggleExclusionRuleStatus() {
	updatingStatus.value = true

	Api.incidentManagement.exclusionRules
		.toggleExclusionRuleStatus(entity.value.id)
		.then(res => {
			if (res.data.success) {
				entity.value.enabled = res.data.exclusion_response.enabled
				emit("updated", res.data.exclusion_response)
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			updatingStatus.value = false
		})
}

watch(updatingStatus, val => {
	emit("loading", val)
})
</script>
