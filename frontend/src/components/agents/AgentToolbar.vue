<template>
	<n-card class="agent-toolbar" content-style="padding:0">
		<div class="wrapper flex flex-col gap-6 py-3 px-4">
			<div class="flex flex-col gap-2">
				<div class="agent-search flex gap-3">
					<n-input v-model:value="textFilter" placeholder="Search for an agent" clearable>
						<template #prefix>
							<Icon :name="SearchIcon" />
						</template>
					</n-input>
					<n-button :loading="syncing" @click="emit('sync')">
						Sync
					</n-button>
				</div>
				<div class="search-info">
					<strong v-if="agentsFilteredLength !== agentsLength">{{ agentsFilteredLength }}</strong>
					<span v-if="agentsFilteredLength !== agentsLength" class="mh-5">/</span>
					<strong class="font-mono">{{ agentsLength }}</strong>
					Agents
				</div>
			</div>

			<div class="agents-list flex grow flex-col overflow-hidden">
				<n-scrollbar>
					<div v-if="agentsCritical?.length" class="agents-critical-list">
						<div class="title">
							Critical Assets
							<small class="text-secondary-color font-mono">({{ agentsCritical.length }})</small>
						</div>
						<div class="list">
							<div
								v-for="agent in agentsCritical"
								:key="agent.agent_id"
								class="item"
								@click="emit('click', agent)"
							>
								{{ agent.hostname }}
							</div>
						</div>
					</div>
					<div v-if="agentsOnline?.length" class="agents-online-list">
						<div class="title">
							Online Agents
							<small class="text-secondary-color font-mono">({{ agentsOnline.length }})</small>
						</div>
						<div class="list">
							<div
								v-for="agent in agentsOnline"
								:key="agent.agent_id"
								class="item"
								@click="emit('click', agent)"
							>
								{{ agent.hostname }}
							</div>
						</div>
					</div>
				</n-scrollbar>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import Icon from "@/components/common/Icon.vue"
import { NButton, NCard, NInput, NScrollbar } from "naive-ui"
import { computed, toRefs } from "vue"

const props = defineProps<{
	modelValue: string
	syncing?: boolean
	agentsLength?: number
	agentsFilteredLength?: number
	agentsCritical?: Agent[]
	agentsOnline?: Agent[]
}>()

const emit = defineEmits<{
	(e: "sync"): void
	(e: "update:modelValue", value: string): void
	(e: "click", value: Agent): void
}>()

const SearchIcon = "carbon:search"

const { modelValue, syncing, agentsLength, agentsFilteredLength, agentsCritical, agentsOnline } = toRefs(props)

const textFilter = computed<string>({
	get() {
		return modelValue.value
	},
	set(value) {
		emit("update:modelValue", value)
	}
})
</script>

<style lang="scss" scoped>
.agent-toolbar {
	container-type: inline-size;
	overflow: hidden;
	max-width: 100%;
	min-width: 340px;

	.wrapper {
		overflow: hidden;
		height: 100%;

		.search-info {
			color: var(--fg-secondary-color);
		}
		.agents-list {
			.title {
				@apply mb-2;
			}

			.list {
				.item {
					border: 2px solid transparent;
					@apply py-2 px-3;
					font-size: 14px;
					font-weight: bold;
					cursor: pointer;
					border-radius: var(--border-radius);

					&:not(:last-child) {
						@apply mb-2;
					}
				}
			}

			.agents-critical-list {
				@apply mb-5;

				.list {
					.item {
						border-color: var(--warning-color);
					}
				}
			}
			.agents-online-list {
				.list {
					.item {
						border-color: var(--success-color);
					}
				}
			}
		}
	}

	@container (min-width: 350px) {
		.wrapper {
			.agent-search {
				flex-grow: 1;
			}
			.search-info {
				display: none;
			}
			.agents-list {
				display: none;
			}
		}
	}
	@media (max-width: 500px) {
		min-width: 100%;

		.wrapper {
			.agent-search {
				flex-grow: 1;
				width: 100%;
			}
			.search-info {
				display: none;
			}
			.agents-list {
				display: none;
			}
		}
	}
}
</style>
