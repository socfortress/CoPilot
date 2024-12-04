<template>
	<div class="page">
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="artifacts" tab="Artifacts" display-directive="show:lazy">
				<ArtifactsList @loaded-agents="agents = $event" @loaded-artifacts="artifacts = $event" />
			</n-tab-pane>
			<n-tab-pane name="collect" tab="Collect" display-directive="show:lazy">
				<ArtifactsCollect
					:agents
					:artifacts
					@loaded-agents="agents = $event"
					@loaded-artifacts="artifacts = $event"
				/>
			</n-tab-pane>
			<n-tab-pane name="command" tab="Command" display-directive="show:lazy">
				<ArtifactsCommand
					:agents
					:artifacts
					@loaded-agents="agents = $event"
					@loaded-artifacts="artifacts = $event"
				/>
			</n-tab-pane>
			<n-tab-pane name="quarantine" tab="Quarantine" display-directive="show:lazy">
				<ArtifactsQuarantine
					:agents
					:artifacts
					@loaded-agents="agents = $event"
					@loaded-artifacts="artifacts = $event"
				/>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import type { Artifact } from "@/types/artifacts.d"
import { NTabPane, NTabs } from "naive-ui"
import { defineAsyncComponent, ref } from "vue"

const ArtifactsList = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsList.vue"))
const ArtifactsCollect = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCollect.vue"))
const ArtifactsCommand = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCommand.vue"))
const ArtifactsQuarantine = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsQuarantine.vue"))

const artifacts = ref<Artifact[]>([])
const agents = ref<Agent[]>([])

const activeTab = ref<string | undefined>(undefined)
</script>
