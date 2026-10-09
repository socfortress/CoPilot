<template>
	<div class="flex flex-col gap-4">
		<p>{{ message }}</p>

		<n-alert v-for="warning of warnings" :key="warning" type="warning" show-icon>
			{{ warning }}
		</n-alert>

		<div v-if="awsConfig" class="flex flex-col gap-3">
			<n-alert :type="awsConfig.detected ? 'error' : 'info'" :title="awsConfig.file_path" show-icon>
				{{ awsConfig.summary }}
			</n-alert>

			<ol class="flex list-decimal flex-col gap-1 pl-5 text-sm">
				<li v-for="step of awsConfig.steps" :key="step">{{ step }}</li>
			</ol>

			<div class="flex flex-col gap-1">
				<span class="text-secondary text-sm">Section to add to {{ awsConfig.file_path }}</span>
				<CodeSource :code="awsConfig.contents" lang="ini" text />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AwsConfigNotice } from "@/api/endpoints/integrations"
import { NAlert } from "naive-ui"
import CodeSource from "@/components/common/CodeSource.vue"

const {
	message,
	warnings = [],
	awsConfig = null
} = defineProps<{
	message: string
	warnings?: string[]
	awsConfig?: AwsConfigNotice | null
}>()
</script>
