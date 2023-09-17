<template>
	<div class="agent-toolbar">
		<div class="wrapper">
			<div class="toolbar-line">
				<div class="agents-header">
					<h2>Agents</h2>
					<el-button @click="emit('sync')" :loading="syncing">
						<i class="mdi mdi-account-sync-outline mr-2 fs-18" v-if="!syncing"></i>
						<span class="ml-6">Sync Agents</span>
					</el-button>
				</div>

				<div class="agent-search">
					<el-input
						:prefix-icon="SearchIcon"
						placeholder="Search for an agent"
						clearable
						v-model="textFilter"
					></el-input>

					<div class="search-info">
						<strong v-if="agentsFilteredLength !== agentsLength">{{ agentsFilteredLength }}</strong>
						<span class="mh-5" v-if="agentsFilteredLength !== agentsLength">/</span>
						<strong>{{ agentsLength }}</strong>
						Agents
					</div>
				</div>
			</div>
			<div class="agents-list scrollable only-y">
				<div class="agents-critical-list" v-if="agentsCritical.length">
					<div class="title">
						Critical Assets
						<small class="o-050">({{ agentsCritical.length }})</small>
					</div>
					<div class="list">
						<div
							class="item"
							v-for="agent in agentsCritical"
							:key="agent.agent_id"
							@click="emit('click', agent)"
						>
							{{ agent.hostname }}
						</div>
					</div>
				</div>
				<div class="agents-online-list" v-if="agentsOnline.length">
					<div class="title">
						Online Agents
						<small class="o-050">({{ agentsOnline.length }})</small>
					</div>
					<div class="list">
						<div
							class="item"
							v-for="agent in agentsOnline"
							:key="agent.agent_id"
							@click="emit('click', agent)"
						>
							{{ agent.hostname }}
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { Agent } from "@/types/agents.d"
import { Search as SearchIcon } from "@element-plus/icons-vue"

const emit = defineEmits<{
	(e: "sync"): void
	(e: "update:modelValue", value: string): void
	(e: "click", value: Agent): void
}>()

const props = defineProps<{
	modelValue: string
	syncing?: boolean
	agentsLength?: number
	agentsFilteredLength?: number
	agentsCritical?: Agent[]
	agentsOnline?: Agent[]
}>()
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
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.agent-toolbar {
	container-type: inline-size;
	@extend .card-base;
	@extend .card-shadow--small;
	overflow: hidden;
	border: 2px solid transparent;
	max-width: 100%;
	min-width: 300px;
	padding: var(--size-3) var(--size-4);
	box-sizing: border-box;
	display: flex;
	flex-direction: column;

	.wrapper {
		display: flex;
		flex-direction: column;
		gap: var(--size-4);
		overflow: hidden;
		flex-grow: 1;

		.toolbar-line {
			display: flex;
			flex-direction: column;
			gap: var(--size-4);
			overflow: hidden;
		}
		.agents-header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: var(--size-3);

			h2 {
				margin: 0;
			}
		}

		.agent-search {
			.search-info {
				opacity: 0.5;
				text-align: right;
				margin-top: var(--size-2);
			}
		}
		.agents-list {
			flex-grow: 1;

			.title {
				margin-bottom: 6px;
			}
			.list {
				.item {
					@extend .card-base;
					@extend .card-shadow--small;
					border: 2px solid transparent;
					padding: var(--size-1) var(--size-2);
					font-size: 14px;
					font-weight: bold;
					cursor: pointer;

					&:not(:last-child) {
						margin-bottom: var(--size-2);
					}
				}
			}

			.agents-critical-list {
				margin-bottom: var(--size-4);

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
			gap: var(--size-3);

			.toolbar-line {
				flex-direction: row;
				align-items: center;
				gap: var(--size-3);
			}

			.agent-search {
				flex-grow: 1;
				.search-info {
					display: none;
				}
			}
			.agents-list {
				display: none;
			}
		}
	}
	@media (max-width: 500px) {
		.wrapper {
			gap: var(--size-3);

			.toolbar-line {
				flex-direction: column;
				gap: var(--size-3);
			}

			.agents-header {
				flex-grow: 1;
				width: 100%;
			}

			.agent-search {
				flex-grow: 1;
				width: 100%;
				.search-info {
					display: none;
				}
			}
			.agents-list {
				display: none;
			}
		}
	}
}
</style>
