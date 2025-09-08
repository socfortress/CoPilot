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
					<div v-if="action.script_parameters.length > 0" class="flex flex-col gap-2">
						<h3 class="text-lg font-semibold">Parameters</h3>
						<div class="overflow-x-auto">
							<table class="w-full border-collapse border border-gray-300">
								<thead>
									<tr class="bg-gray-50">
										<th class="border border-gray-300 px-3 py-2 text-left">Name</th>
										<th class="border border-gray-300 px-3 py-2 text-left">Type</th>
										<th class="border border-gray-300 px-3 py-2 text-left">Required</th>
										<th class="border border-gray-300 px-3 py-2 text-left">Description</th>
										<th class="border border-gray-300 px-3 py-2 text-left">Default</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="param in action.script_parameters" :key="param.name">
										<td class="border border-gray-300 px-3 py-2 font-mono text-sm">{{ param.name }}</td>
										<td class="border border-gray-300 px-3 py-2">
											<Badge color="primary">
												<template #value>{{ param.type }}</template>
											</Badge>
										</td>
										<td class="border border-gray-300 px-3 py-2">
											<Badge :color="param.required ? 'danger' : 'success'">
												<template #value>{{ param.required ? 'Yes' : 'No' }}</template>
											</Badge>
										</td>
										<td class="border border-gray-300 px-3 py-2">{{ param.description || '-' }}</td>
										<td class="border border-gray-300 px-3 py-2 font-mono text-sm">
											{{ param.default !== null && param.default !== undefined ? param.default : '-' }}
										</td>
									</tr>
								</tbody>
							</table>
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

table {
	font-size: 0.9em;
}

th {
	font-weight: 600;
}
</style>
