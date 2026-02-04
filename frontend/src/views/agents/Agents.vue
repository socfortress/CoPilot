<template>
	<div class="page page-wrapped page-without-footer flex flex-col">
		<div class="wrapper flex grow gap-4">
			<div class="sidebar">
				<AgentToolbar
					v-model="textFilter"
					:syncing="loadingSync"
					:agents-length="agents.length"
					:agents-filtered-length="agentsFiltered.length"
					:agents-critical="agentsCritical"
					:agents-online="agentsOnline"
					:selection-mode="selectionMode"
					:selected-count="selectedAgents.length"
					@run="runCommand($event)"
					@click="gotoAgent($event.agent_id)"
					@bulk-delete="showBulkDeleteModal = true"
					@update:selection-mode="selectionMode = $event"
					@clear-selection="clearSelection"
				/>
			</div>
			<div class="main flex grow flex-col overflow-hidden">
				<n-spin class="flex h-full w-full flex-col overflow-hidden" :show="loadingAgents">
					<n-scrollbar class="grow">
						<div class="agents-list flex grow flex-col gap-3">
							<template v-if="agentsFiltered.length">
								<AgentCard
									v-for="agent in itemsPaginated"
									:key="agent.agent_id"
									:agent
									:show-actions="!selectionMode"
									:selectable="selectionMode"
									:selected="isAgentSelected(agent)"
									hoverable
									clickable
									class="item-appear item-appear-bottom item-appear-005"
									@delete="syncAgents()"
									@click="handleAgentClick(agent)"
									@toggle-selection="toggleAgentSelection(agent)"
								/>
							</template>
							<template v-else>
								<n-empty
									v-if="!loadingAgents"
									description="No items found"
									class="h-48 justify-center"
								/>
							</template>
						</div>
					</n-scrollbar>
				</n-spin>

				<div class="pagination-wrapper">
					<n-pagination
						v-model:page="page"
						:page-size="pageSize"
						:page-slot="5"
						:item-count="agentsFiltered.length"
					/>
				</div>
			</div>
		</div>

		<!-- Bulk Delete Modal -->
		<BulkDeleteModal
			v-model:show="showBulkDeleteModal"
			:selected-agents="selectedAgents"
			:customers="uniqueCustomers"
			@remove-selection="removeFromSelection"
			@deleted="onBulkDeleteComplete"
		/>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import _debounce from "lodash/debounce"
import _split from "lodash/split"
import { NEmpty, NPagination, NScrollbar, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import AgentCard from "@/components/agents/AgentCard.vue"
import AgentToolbar from "@/components/agents/AgentToolbar.vue"
import BulkDeleteModal from "@/components/agents/BulkDeleteModal.vue"
import { useGoto } from "@/composables/useGoto"
import { AgentStatus } from "@/types/agents.d"

const message = useMessage()
const { gotoAgent } = useGoto()
const loadingAgents = ref(false)
const loadingSync = ref(false)
const agents = ref<Agent[]>([])
const textFilter = ref("")
const page = ref(1)
const pageSize = ref(20)

// Selection mode state
const selectionMode = ref(false)
const selectedAgents = ref<Agent[]>([])
const showBulkDeleteModal = ref(false)

const textFilterDebounced = ref("")

const update = _debounce(value => {
    textFilterDebounced.value = value
}, 100)

watch(textFilter, val => {
    update(val)
})

const agentsFiltered = computed(() => {
    return agents.value
        .filter(({ hostname, ip_address, agent_id, label }) =>
            (hostname + ip_address + agent_id + label)
                .toString()
                .toLowerCase()
                .includes(textFilterDebounced.value.toString().toLowerCase())
        )
        .sort((a, b) => Number.parseInt(a.agent_id) - Number.parseInt(b.agent_id))
})

const itemsPaginated = computed(() => {
    const from = (page.value - 1) * pageSize.value
    const to = page.value * pageSize.value

    return agentsFiltered.value.slice(from, to)
})

const agentsCritical = computed(() => {
    return agents.value.filter(({ critical_asset }) => critical_asset)
})

const agentsOnline = computed(() => {
    return agents.value.filter(({ wazuh_agent_status }) => wazuh_agent_status === AgentStatus.Active)
})

// Get unique customer codes for filter dropdown
const uniqueCustomers = computed(() => {
    const codes = new Set(agents.value.map(a => a.customer_code).filter(Boolean))
    return Array.from(codes) as string[]
})

// Selection helpers
function isAgentSelected(agent: Agent): boolean {
    return selectedAgents.value.some(a => a.agent_id === agent.agent_id)
}

function toggleAgentSelection(agent: Agent) {
    const index = selectedAgents.value.findIndex(a => a.agent_id === agent.agent_id)
    if (index === -1) {
        selectedAgents.value.push(agent)
    } else {
        selectedAgents.value.splice(index, 1)
    }
}

function removeFromSelection(agent: Agent) {
    const index = selectedAgents.value.findIndex(a => a.agent_id === agent.agent_id)
    if (index !== -1) {
        selectedAgents.value.splice(index, 1)
    }
}

function clearSelection() {
    selectedAgents.value = []
}

function handleAgentClick(agent: Agent) {
    if (selectionMode.value) {
        toggleAgentSelection(agent)
    } else {
        gotoAgent(agent.agent_id)
    }
}

function onBulkDeleteComplete() {
    clearSelection()
    selectionMode.value = false
    getAgents()
}

function runCommand(command: string) {
    if (command === "sync-agents") {
        syncAgents()
    } else if (_split(command, ":").length) {
        syncVulnerabilities(_split(command, ":")[1])
    }
}

function getAgents() {
    loadingAgents.value = true

    Api.agents
        .getAgents()
        .then(res => {
            if (res.data.success) {
                agents.value = res.data.agents || []
            } else {
                message.error(res.data?.message || "An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            message.error(err.response?.data?.message || "An error occurred. Please try again later.")
        })
        .finally(() => {
            loadingAgents.value = false
        })
}

function syncAgents() {
    loadingSync.value = true

    Api.agents
        .syncAgents()
        .then(res => {
            if (res.data.success) {
                message.success("Agents Synced Successfully")
                getAgents()
            } else {
                message.error("An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            if (err.response?.status === 401) {
                message.error(err.response?.data?.message || "Sync returned Unauthorized.")
            } else {
                message.error(err.response?.data?.message || "Failed to Sync Agents")
            }
        })
        .finally(() => {
            loadingSync.value = false
        })
}

function syncVulnerabilities(customerCode: string) {
    loadingSync.value = true

    Api.agents
        .syncVulnerabilities(customerCode)
        .then(res => {
            if (res.data.success) {
                message.success("Agent vulnerabilities synced successfully")
                getAgents()
            } else {
                message.error("An error occurred. Please try again later.")
            }
        })
        .catch(err => {
            if (err.response?.status === 401) {
                message.error(err.response?.data?.message || "Sync returned Unauthorized.")
            } else {
                message.error(err.response?.data?.message || "Failed to Sync Agents")
            }
        })
        .finally(() => {
            loadingSync.value = false
        })
}

onBeforeMount(() => {
    getAgents()
})
</script>

<style lang="scss" scoped>
.page {
    container-type: inline-size;

    .wrapper {
        position: relative;
        height: 100%;
        overflow: hidden;

        .sidebar {
            .agent-toolbar {
                height: 100%;
            }
        }

        :deep() {
            .n-spin-content {
                overflow: hidden;
                max-height: 100%;
            }
        }

        .main {
            position: relative;
            border-radius: var(--border-radius);

            :deep() {
                .n-scrollbar > .n-scrollbar-rail.n-scrollbar-rail--vertical {
                    right: 0;
                    bottom: 50px;
                }
            }

            .pagination-wrapper {
                --size: 10px;
                position: absolute;
                bottom: 0;
                right: 0;
                background-color: var(--bg-body-color);
                padding-left: var(--size);
                padding-top: var(--size);
                border-top-left-radius: var(--size);

                &::before,
                &::after {
                    content: "";
                    position: absolute;
                    width: var(--size);
                    height: var(--size);
                    left: calc(var(--size) * -1);
                    display: block;
                    bottom: 0px;
                    z-index: 1;
                    background-image: radial-gradient(
                        circle at 0 0,
                        rgba(0, 0, 0, 0) calc(var(--size) - 1px),
                        var(--bg-body-color) calc(var(--size) + 0px)
                    );
                }

                &::after {
                    bottom: initial;
                    left: initial;
                    top: calc(var(--size) * -1);
                    right: 0;
                }
            }
        }

        .agents-list {
            width: 100%;

            .item-appear {
                &:last-child {
                    margin-bottom: 50px;
                }
            }
        }
    }
    @container (max-width: 770px) {
        .wrapper {
            flex-direction: column;
        }
    }
}
</style>
