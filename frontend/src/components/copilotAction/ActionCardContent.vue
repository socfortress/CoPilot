<template>
	<div class="flex flex-col gap-4 pb-1">
		<!-- Basic Information -->
		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			<CardKV>
				<template #key>Information</template>
				<template #value>
					<div class="flex flex-col gap-2 py-0.5">
						<div class="flex flex-wrap gap-2">
							<strong>Technology:</strong>
							<span>{{ action.technology }}</span>
						</div>
						<div v-if="action.category" class="flex flex-wrap gap-2">
							<strong>Category:</strong>
							<span>{{ action.category }}</span>
						</div>
						<div v-if="action.version" class="flex flex-wrap gap-2">
							<strong>Version:</strong>
							<span>{{ action.version }}</span>
						</div>
						<div v-if="action.last_updated" class="flex flex-wrap gap-2">
							<strong>Last Updated:</strong>
							<span>{{ formatDate(action.last_updated, dFormats.datetime) }}</span>
						</div>
					</div>
				</template>
			</CardKV>
			<CardKV>
				<template #key>Script Details</template>
				<template #value>
					<div class="flex flex-col gap-2 py-0.5">
						<div v-if="action.script_name" class="flex flex-wrap gap-2">
							<strong>Script Name:</strong>
							<span>{{ action.script_name }}</span>
						</div>
						<div class="flex flex-wrap gap-2">
							<strong>Repository:</strong>
							<a :href="action.repo_url" target="_blank" rel="noopener">
								{{ action.repo_url }}
							</a>
						</div>
					</div>
				</template>
			</CardKV>
		</div>

		<!-- Description -->
		<CardKV>
			<template #key>Description</template>
			<template #value>{{ action.description }}</template>
		</CardKV>

		<!-- Parameters -->
		<CardKV v-if="action.script_parameters?.length">
			<template #key>Parameters</template>
			<template #value>
				<div class="grid grid-cols-1 gap-3 py-1 lg:grid-cols-2">
					<CardEntity
						v-for="param in action.script_parameters"
						:key="param.name"
						embedded
						size="small"
						class="h-full"
						main-box-class="grow"
						card-entity-wrapper-class="h-full"
					>
						<template #headerMain>
							<div class="text-default flex items-center gap-4">
								<div class="text-sm font-semibold">{{ param.name }}</div>
								<Badge :color="param.required ? 'danger' : 'success'" type="splitted">
									<template #value>
										<span class="text-xs">{{ param.required ? "Required" : "Optional" }}</span>
									</template>
								</Badge>
							</div>
						</template>
						<template #headerExtra>
							<Badge>
								<template #value>
									<span class="text-xs">{{ param.type }}</span>
								</template>
							</Badge>
						</template>

						<template v-if="param.description" #default>
							<p class="text-xs">{{ param.description }}</p>
						</template>

						<template #footer>
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
						</template>
					</CardEntity>
				</div>
			</template>
		</CardKV>

		<!-- Tags -->
		<div v-if="action.tags?.length" class="flex flex-wrap gap-2">
			<code v-for="tag of action.tags" :key="tag">#{{ tag }}</code>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { action } = defineProps<{
	action: ActiveResponseItem
}>()

const dFormats = useSettingsStore().dateFormat
</script>
