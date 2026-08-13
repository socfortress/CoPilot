<template>
	<div class="flex flex-col-reverse gap-6 lg:flex-row">
		<div
			class="border-primary shrink-0 overflow-hidden rounded-lg border-2 bg-white p-4 pt-12 lg:p-8"
			:class="customerCode ? 'lg:w-100' : 'lg:w-120'"
		>
			<Preview class="mx-auto" :title="previewData?.title" :logo="previewData?.logo" />
		</div>

		<n-card class="grow">
			<SettingsForm :customer-code @update="previewData = $event" />
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { SettingsModel } from "./Form.vue"
import { NCard } from "naive-ui"
import { ref } from "vue"
import SettingsForm from "./Form.vue"
import Preview from "./Preview.vue"

/**
 * Login-page preview + branding form. Serves both scopes: the global portal
 * defaults (no `customerCode`) and a single customer's override (`customerCode`).
 */
const { customerCode } = defineProps<{
	customerCode?: string
}>()

const previewData = ref<SettingsModel | null>(null)
</script>
