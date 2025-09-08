<template>
	<div class="action-details">
		<n-spin :show="loading" class="min-h-48">
			<template v-if="action">
				<div class="flex flex-col gap-4">
					<!-- Basic Information -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div class="flex flex-col gap-2">
							<h3 class="text-lg font-semibold">Information</h3>
							<div class="flex flex-col gap-1">
								<div><strong>Technology:</strong> {{ action.technology }}</div>
								<div v-if="action.category"><strong>Category:</strong> {{ action.category }}</div>
								<div v-if="action.version"><strong>Version:</strong> {{ action.version }}</div>
								<div v-if="action.last_updated"><strong>Last Updated:</strong> {{ formatDate(action.last_updated) }}</div>
							</div>
						</div>
						<div class="flex flex-col gap-2">
							<h3 class="text-lg font-semibold">Script Details</h3>
							<div class="flex flex-col gap-1">
								<div v-if="action.script_name"><strong>Script Name:</strong> {{ action.script_name }}</div>
								<div>
									<strong>Repository:</strong>
									<a :href="action.repo_url" target="_blank" class="text-blue-500 hover:underline">
										{{ action.repo_url }}
									</a>
								</div>
							</div>
						</div>
					</div>

					<!-- Description -->
					<div class="flex flex-col gap-2">
						<h3 class="text-lg font-semibold">Description</h3>
						<p class="text-gray-600">{{ action.description }}</p>
					</div>

					<!-- Tags -->
					<div v-if="action.tags && action.tags.length > 0" class="flex flex-col gap-2">
						<h3 class="text-lg font-semibold">Tags</h3>
						<div class="flex flex-wrap gap-2">
							<Badge v-for="tag of action.tags" :key="tag">
								<template #value>{{ tag }}</template>
							</Badge>
						</div>
					</div>

					<!-- Parameters -->
					<div v-if="action.script_parameters.length > 0" class="flex flex-col gap-4">
						<h3 class="text-lg font-semibold">Parameters</h3>
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
							<div
								v-for="param in action.script_parameters"
								:key="param.name"
								class="bg-gray-50 border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
							>
								<div class="flex items-start justify-between mb-2">
									<div class="flex items-center gap-2">
										<h4 class="font-mono text-sm font-semibold text-gray-900">{{ param.name }}</h4>
										<Badge :color="param.required ? 'danger' : 'success'" size="small">
											<template #value>{{ param.required ? 'Required' : 'Optional' }}</template>
										</Badge>
									</div>
									<Badge color="primary" size="small">
										<template #value>{{ param.type }}</template>
									</Badge>
								</div>

								<div v-if="param.description" class="text-sm text-gray-600 mb-3">
									{{ param.description }}
								</div>

								<div class="flex flex-col gap-1">
									<div v-if="param.default !== null && param.default !== undefined" class="text-xs text-gray-500">
										<span class="font-medium">Default:</span>
										<code class="bg-gray-200 px-1 py-0.5 rounded text-xs">{{ param.default }}</code>
									</div>

									<div v-if="param.enum && param.enum.length > 0" class="text-xs text-gray-500">
										<span class="font-medium">Options:</span>
										<div class="flex flex-wrap gap-1 mt-1">
											<code
												v-for="option in param.enum"
												:key="option"
												class="bg-blue-100 text-blue-800 px-1 py-0.5 rounded text-xs"
											>
												{{ option }}
											</code>
										</div>
									</div>

									<div v-if="param.arg_position" class="text-xs text-gray-500">
										<span class="font-medium">Position:</span> {{ param.arg_position }}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No action details found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import { NEmpty, NSpin } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"

const { action } = defineProps<{
	action: ActiveResponseItem
}>()

const loading = ref(false)

function formatDate(date: Date): string {
	return new Date(date).toLocaleDateString()
}
</script>

<style scoped>
.action-details {
	max-height: 70vh;
	overflow-y: auto;
}

/* Custom scrollbar for better UX */
.action-details::-webkit-scrollbar {
	width: 6px;
}

.action-details::-webkit-scrollbar-track {
	background: #f1f1f1;
	border-radius: 3px;
}

.action-details::-webkit-scrollbar-thumb {
	background: #c1c1c1;
	border-radius: 3px;
}

.action-details::-webkit-scrollbar-thumb:hover {
	background: #a8a8a8;
}

/* Parameter card hover effects */
.bg-gray-50:hover {
	background-color: #f8fafc;
}
</style>
