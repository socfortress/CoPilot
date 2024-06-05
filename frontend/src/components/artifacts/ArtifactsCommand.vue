<template>
	<div class="artifacts-command">
		<div class="header flex items-start gap-2">
			<div class="flex flex-col gap-2 w-full">
				<div class="grow flex items-center gap-2 flex-wrap">
					<div class="grow basis-56" v-if="!hideHostnameField">
						<n-select
							v-model:value="filters.hostname"
							:options="agentHostnameOptions"
							placeholder="Agent hostname"
							clearable
							filterable
							size="small"
							:disabled="loading"
							:loading="loadingAgents"
						/>
					</div>
					<div class="grow basis-56">
						<n-select
							v-model:value="filters.artifact_name"
							:options="artifactsOptions"
							placeholder="Artifact name"
							clearable
							filterable
							size="small"
							:disabled="loading"
							:loading="loadingArtifacts"
						/>
					</div>
					<div class="grow basis-56" v-if="!hideVelociraptorIdField">
						<n-input
							v-model:value="filters.velociraptor_id"
							placeholder="Velociraptor id"
							:readonly="loading"
							clearable
							size="small"
						/>
					</div>
				</div>
				<div class="grow flex items-center gap-2 flex-wrap">
					<n-input
						v-model:value="filters.command"
						placeholder="Command"
						clearable
						:readonly="loading"
						type="textarea"
						:autosize="{
							minRows: 3,
							maxRows: 10
						}"
					/>
				</div>
				<div class="grow flex items-center justify-end gap-2 flex-wrap-reverse">
					<div class="badges-box flex gap-2 flex-wrap grow">
						<n-tooltip trigger="hover" v-if="commandTime">
							<template #trigger>
								<Badge type="splitted" hint-cursor>
									<template #iconLeft>
										<Icon :name="TimeIcon"></Icon>
									</template>
									<template #value>
										<span class="flex">
											{{ formatDate(commandTime, dFormats.timesec) }}

											<n-spin :size="12" v-if="loading" class="ml-2" />

											{{ responseTime ? " / " + formatDate(responseTime, dFormats.timesec) : "" }}
										</span>
									</template>
								</Badge>
							</template>
							Last request time / last response time
						</n-tooltip>

						<Badge type="splitted" v-if="diffTime">
							<template #iconLeft>
								<Icon :name="StopWatchIcon" :size="15"></Icon>
							</template>
							<template #value>
								{{ diffTime }}
							</template>
						</Badge>
					</div>
					<n-button
						size="small"
						@click="getData()"
						type="primary"
						secondary
						:loading="loading"
						:disabled="!areFiltersValid"
					>
						Submit
					</n-button>
				</div>
			</div>
		</div>
		<n-spin :show="loading">
			<div class="list flex flex-col gap-3 my-7">
				<template v-if="commandList.length">
					<CommandItem
						v-for="command of commandList"
						:key="command.Stdout"
						:command="command"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, computed, nextTick } from "vue"
import { useMessage, NSpin, NButton, NEmpty, NSelect, NInput, NTooltip } from "naive-ui"
import Api from "@/api"
import CommandItem from "./CommandItem.vue"
import Badge from "@/components/common/Badge.vue"
import type { Agent } from "@/types/agents.d"
import type { CommandRequest } from "@/api/artifacts"
import type { Artifact, CommandResult } from "@/types/artifacts.d"
import dayjs from "@/utils/dayjs"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
// import { commandResult } from "./mock"

const emit = defineEmits<{
	(e: "loaded-agents", value: Agent[]): void
	(e: "loaded-artifacts", value: Artifact[]): void
}>()

const props = defineProps<{
	hostname?: string
	agents?: Agent[]
	artifacts?: Artifact[]
	hideHostnameField?: boolean
	hideVelociraptorIdField?: boolean
}>()
const { hostname, agents, artifacts, hideHostnameField, hideVelociraptorIdField } = toRefs(props)

const TimeIcon = "carbon:time"
const StopWatchIcon = "quill:stopwatch"

const message = useMessage()
const loadingAgents = ref(false)
const loadingArtifacts = ref(false)
const loading = ref(false)
const agentsList = ref<Agent[]>([])
const artifactsList = ref<Artifact[]>([])
const commandList = ref<CommandResult[]>([])
const commandTime = ref<Date | null>(null)
const responseTime = ref<Date | null>(null)
const dFormats = useSettingsStore().dateFormat

const diffTime = computed(() => {
	if (commandTime.value && responseTime.value) {
		return dayjs.duration(dayjs(responseTime.value).diff(commandTime.value, "ms", true)).asSeconds() + "s"
	} else {
		return null
	}
})

const filters = ref<Partial<CommandRequest>>({})

const areFiltersValid = computed(() => {
	return !!filters.value.artifact_name && !!filters.value.hostname && !!filters.value.command
})

const agentHostnameOptions = computed(() => {
	if (hostname?.value) {
		return [{ value: hostname.value, label: hostname.value }]
	}
	return (agentsList.value || []).map(o => ({ value: o.hostname, label: o.hostname }))
})

const artifactsOptions = computed(() => {
	return (artifactsList.value || []).map(o => ({ value: o.name, label: o.name }))
})

function getData() {
	if (areFiltersValid.value) {
		loading.value = true
		commandList.value = []
		commandTime.value = new Date()
		responseTime.value = null

		Api.artifacts
			.command(filters.value as CommandRequest)
			.then(res => {
				if (res.data.success) {
					commandList.value = res.data?.results || []
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				responseTime.value = new Date()
				loading.value = false
			})
	}
}

function getAgents(cb?: (agents: Agent[]) => void) {
	loadingAgents.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agentsList.value = res.data.agents || []

				if (cb && typeof cb === "function") {
					cb(agentsList.value)
				}
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

function getArtifacts(cb?: (artifacts: Artifact[]) => void) {
	loadingArtifacts.value = true

	Api.artifacts
		.getAll()
		.then(res => {
			if (res.data.success) {
				artifactsList.value = res.data.artifacts || []

				if (cb && typeof cb === "function") {
					cb(artifactsList.value)
				}
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingArtifacts.value = false
		})
}

onBeforeMount(() => {
	artifactsList.value = ["Windows.System.PowerShell", "Windows.System.CmdShell", "Linux.Sys.BashShell"].map(
		o => ({ name: o }) as Artifact
	)

	if (hostname?.value) {
		filters.value.hostname = hostname.value
	}

	if (agents?.value?.length && !agentsList.value.length) {
		agentsList.value = agents.value
	}

	if (artifacts?.value?.length && !artifactsList.value.length) {
		artifactsList.value = artifacts.value
	}

	nextTick(() => {
		if (!agentsList.value.length && !hostname?.value) {
			getAgents((agents: Agent[]) => {
				emit("loaded-agents", agents)
			})
		}
		if (!artifactsList.value.length) {
			getArtifacts((artifacts: Artifact[]) => {
				emit("loaded-artifacts", artifacts)
			})
		}
	})

	// MOCK
	// commandList.value = commandResult as CommandResult[]
})
</script>

<style lang="scss" scoped>
.artifacts-command {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
