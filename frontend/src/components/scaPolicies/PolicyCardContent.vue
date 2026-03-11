<template>
	<div class="flex flex-col gap-4 pb-1">
		<!-- Policy Information -->
		<PropsList :list="infoFields" embedded title="Policy Information" />

		<!-- Description -->
		<CardKV>
			<template #key>Description</template>
			<template #value>{{ policy.description }}</template>
		</CardKV>

		<!-- Agent Detection -->
		<CardKV>
			<template #key>
				<div class="flex items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						<Icon :name="AgentsIcon" :size="14" />
						<span>Agents with {{ policy.application }}</span>
					</div>
					<n-button
						v-if="!agentsLoaded"
						size="tiny"
						type="primary"
						secondary
						:loading="loadingAgents"
						@click="detectAgents"
					>
						<template #icon>
							<Icon :name="SearchIcon" />
						</template>
						Detect Agents
					</n-button>
				</div>
			</template>
			<template #value>
				<n-spin :show="loadingAgents">
					<div v-if="agentsLoaded">
						<div v-if="agentsResponse && agentsResponse.matched_agents.length" class="flex flex-col gap-3">
							<div class="text-xs opacity-60">
								Found
								<strong>{{ agentsResponse.total }}</strong>
								agent(s) with
								<strong>{{ agentsResponse.display_name }}</strong>
								installed
							</div>
							<div class="grid grid-cols-1 gap-3 py-1 lg:grid-cols-2">
								<CardEntity
									v-for="agent in agentsResponse.matched_agents"
									:key="`${agent.agent_id}-${agent.package_name}`"
									embedded
									size="small"
									class="h-full"
									main-box-class="grow"
									card-entity-wrapper-class="h-full"
								>
									<template #headerMain>
										<div class="text-default flex items-center gap-2">
											<span class="text-sm font-semibold">
												{{ agent.agent_name || "Unknown" }}
											</span>
											<Badge size="small">
												<template #value>ID: {{ agent.agent_id }}</template>
											</Badge>
										</div>
									</template>
									<template #default>
										<div class="flex flex-wrap gap-2 text-xs">
											<Badge type="splitted" size="small">
												<template #label>Package</template>
												<template #value>{{ agent.package_name }}</template>
											</Badge>
											<Badge v-if="agent.package_version" type="splitted" size="small">
												<template #label>Version</template>
												<template #value>{{ agent.package_version }}</template>
											</Badge>
											<Badge v-if="agent.package_architecture" type="splitted" size="small">
												<template #label>Arch</template>
												<template #value>{{ agent.package_architecture }}</template>
											</Badge>
										</div>
									</template>
								</CardEntity>
							</div>
						</div>
						<n-empty
							v-else
							description="No agents found with this package installed"
							class="h-24 justify-center"
						/>
					</div>
					<div v-else class="text-secondary text-sm">
						Click "Detect Agents" to search for agents running {{ policy.application }}
					</div>
				</n-spin>
			</template>
		</CardKV>

		<!-- Applicable Policies -->
		<CardKV v-if="agentsResponse?.applicable_policies?.length">
			<template #key>Applicable SCA Policies</template>
			<template #value>
				<div class="flex flex-wrap gap-2">
					<Badge v-for="ap of agentsResponse.applicable_policies" :key="ap.id" color="primary">
						<template #value>{{ ap.name }}</template>
					</Badge>
				</div>
			</template>
		</CardKV>

		<!-- Policy YAML Content -->
		<CardKV>
			<template #key>
				<div class="flex items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						<Icon :name="CodeIcon" :size="14" />
						<span>Policy YAML</span>
					</div>
					<n-button
						v-if="!yamlLoaded"
						size="tiny"
						type="primary"
						secondary
						:loading="loadingYaml"
						@click="loadYamlContent"
					>
						<template #icon>
							<Icon :name="DownloadIcon" />
						</template>
						Load YAML
					</n-button>
				</div>
			</template>
			<template #value>
				<n-spin :show="loadingYaml">
					<div v-if="yamlLoaded">
						<CodeSource v-if="yamlContent" :code="yamlContent" lang="yaml" />
						<n-empty v-else description="Failed to load YAML content" class="h-24 justify-center" />
					</div>
					<div v-else class="text-secondary text-sm">Click "Load YAML" to preview the policy content</div>
				</n-spin>
			</template>
		</CardKV>
	</div>
</template>

<script setup lang="ts">
import type { ScaPolicyItem, ScaPackageAgentsResponse } from "@/types/sca.d"
import { computed, ref } from "vue"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import PropsList from "@/components/common/PropsList.vue"

const props = defineProps<{ policy: ScaPolicyItem }>()

const message = useMessage()

const loadingAgents = ref(false)
const agentsLoaded = ref(false)
const agentsResponse = ref<ScaPackageAgentsResponse | null>(null)

const loadingYaml = ref(false)
const yamlLoaded = ref(false)
const yamlContent = ref<string | null>(null)

const AgentsIcon = "carbon:devices"
const SearchIcon = "carbon:search"
const CodeIcon = "carbon:code"
const DownloadIcon = "carbon:download"

const infoFields = computed(() => ({
	id: props.policy.id,
	application: props.policy.application,
	app_version: props.policy.app_version,
	platform: props.policy.platform,
	cis_version: props.policy.cis_version
}))

function getRegistryKey(application: string): string | null {
	const app = application.toLowerCase()
	if (app.includes("apache")) return "apache"
	if (app.includes("nginx")) return "nginx"
	if (app.includes("iis")) return "iis"
	if (app.includes("mysql") || app.includes("mariadb")) return "mysql"
	if (app.includes("postgresql") || app.includes("postgres")) return "postgresql"
	if (app === "sqlserver" || app.includes("sql server") || app.includes("mssql")) return "sqlserver"
	return null
}

async function detectAgents() {
	const registryKey = getRegistryKey(props.policy.application)
	if (!registryKey) {
		message.warning(`No package registry mapping for "${props.policy.application}"`)
		agentsLoaded.value = true
		return
	}

	loadingAgents.value = true
	try {
		const res = await Api.sca.getAgentsForPackage(registryKey)
		if (res.data.success) {
			agentsResponse.value = res.data
		} else {
			message.warning(res.data?.message || "Failed to detect agents")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to detect agents")
	} finally {
		loadingAgents.value = false
		agentsLoaded.value = true
	}
}

async function loadYamlContent() {
	loadingYaml.value = true
	try {
		const res = await Api.sca.getPolicyContent(props.policy.id)
		if (res.data.success) {
			yamlContent.value = res.data.content
		} else {
			message.warning(res.data?.message || "Failed to load policy content")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load policy content")
	} finally {
		loadingYaml.value = false
		yamlLoaded.value = true
	}
}
</script>
