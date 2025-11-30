<template>
	<div class="flex flex-col-reverse gap-6 lg:flex-row">
		<div class="border-primary shrink-0 overflow-hidden rounded-lg border-2 bg-white p-4 pt-12 lg:w-120 lg:p-8">
			<Preview class="mx-auto" :title="previewData?.title" :logo="previewData?.logo" />
		</div>

		<n-card class="grow">
			<SettingsForm @update="previewData = $event" />
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { SettingsModel } from "./Form.vue"
import { NCard } from "naive-ui"
import { ref } from "vue"
import SettingsForm from "./Form.vue"
import Preview from "./Preview.vue"

const previewData = ref<SettingsModel | null>(null)
</script>
