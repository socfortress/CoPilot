<template>
	<div class="action-details">
		<n-spin :show="loading" class="min-h-48" content-class="flex flex-col gap-4">
			<!-- Basic Information -->
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<div class="flex flex-col gap-2">
					<h3 class="text-lg font-semibold">Information</h3>
					<div class="flex flex-col gap-1">
						<div>
							<strong>Technology:</strong>
							{{ action.technology }}
						</div>
						<div v-if="action.category">
							<strong>Category:</strong>
							{{ action.category }}
						</div>
						<div v-if="action.version">
							<strong>Version:</strong>
							{{ action.version }}
						</div>
						<div v-if="action.last_updated">
							<strong>Last Updated:</strong>
							{{ formatDate(action.last_updated) }}
						</div>
					</div>
				</div>
				<div class="flex flex-col gap-2">
					<h3 class="text-lg font-semibold">Script Details</h3>
					<div class="flex flex-col gap-1">
						<div v-if="action.script_name">
							<strong>Script Name:</strong>
							{{ action.script_name }}
						</div>
						<div>
							<strong>Repository:</strong>
							<a :href="action.repo_url" target="_blank" rel="noopener">
								{{ action.repo_url }}
							</a>
						</div>
					</div>
				</div>
			</div>

			<!-- Description -->
			<div class="flex flex-col gap-2">
				<h3 class="text-lg font-semibold">Description</h3>
				<p class="text-base font-medium leading-relaxed opacity-90">{{ action.description }}</p>
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
				<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
					<div
						v-for="param in action.script_parameters"
						:key="param.name"
						class="parameter-card rounded-lg border p-4 transition-shadow hover:shadow-sm"
					>
						<div class="mb-2 flex items-start justify-between">
							<div class="flex items-center gap-2">
								<h4 class="font-mono text-sm font-semibold">{{ param.name }}</h4>
								<Badge :color="param.required ? 'danger' : 'success'" size="small">
									<template #value>{{ param.required ? "Required" : "Optional" }}</template>
								</Badge>
							</div>
							<Badge color="primary" size="small">
								<template #value>{{ param.type }}</template>
							</Badge>
						</div>

						<div v-if="param.description" class="mb-3 text-sm opacity-75">
							{{ param.description }}
						</div>

						<div class="flex flex-col gap-1">
							<div
								v-if="param.default !== null && param.default !== undefined"
								class="text-xs opacity-60"
							>
								<span class="font-medium">Default:</span>
								<code class="code-block ml-1 rounded px-1 py-0.5 text-xs">
									{{ param.default }}
								</code>
							</div>

							<div v-if="param.enum && param.enum.length > 0" class="text-xs opacity-60">
								<span class="font-medium">Options:</span>
								<div class="mt-1 flex flex-wrap gap-1">
									<code
										v-for="option in param.enum"
										:key="option"
										class="enum-option rounded px-1 py-0.5 text-xs"
									>
										{{ option }}
									</code>
								</div>
							</div>

							<div v-if="param.arg_position" class="text-xs opacity-60">
								<span class="font-medium">Position:</span>
								{{ param.arg_position }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import { NSpin } from "naive-ui"
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
	background: var(--border-color);
	border-radius: 3px;
}

.action-details::-webkit-scrollbar-thumb {
	background: var(--text-color-3);
	border-radius: 3px;
}

.action-details::-webkit-scrollbar-thumb:hover {
	background: var(--text-color-2);
}

/* Parameter cards */
.parameter-card {
	background-color: var(--card-color);
	border-color: var(--border-color);
	transition: all 0.2s ease;
}

.parameter-card:hover {
	background-color: var(--hover-color);
	border-color: var(--border-color-hover);
	box-shadow:
		0 1px 3px 0 rgba(0, 0, 0, 0.1),
		0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

/* Code blocks */
.code-block {
	background-color: var(--code-color);
	color: var(--text-color-1);
	border: 1px solid var(--border-color);
}

.enum-option {
	background-color: var(--primary-color-hover);
	color: var(--primary-color);
	border: 1px solid var(--primary-color-hover);
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
	.parameter-card:hover {
		box-shadow:
			0 1px 3px 0 rgba(255, 255, 255, 0.1),
			0 1px 2px 0 rgba(255, 255, 255, 0.06);
	}
}
</style>
