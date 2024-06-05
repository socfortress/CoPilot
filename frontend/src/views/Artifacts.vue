<template>
	<div class="page">
		<n-tabs type="line" animated v-model:value="activeTab">
			<n-tab-pane name="artifacts" tab="Artifacts" display-directive="show:lazy">
				<ArtifactsList @loaded-agents="agents = $event" @loaded-artifacts="artifacts = $event" />
			</n-tab-pane>
			<n-tab-pane name="collect" tab="Collect" display-directive="show:lazy">
				<ArtifactsCollect
					@loaded-agents="agents = $event"
					@loaded-artifacts="artifacts = $event"
					:agents
					:artifacts
				/>
			</n-tab-pane>
			<n-tab-pane name="command" tab="Command" display-directive="show:lazy">
				<ArtifactsCommand
					@loaded-agents="agents = $event"
					@loaded-artifacts="artifacts = $event"
					:agents
					:artifacts
				/>
			</n-tab-pane>
			<n-tab-pane name="quarantine" tab="Quarantine" display-directive="show:lazy">
				<ArtifactsQuarantine
					@loaded-agents="agents = $event"
					@loaded-artifacts="artifacts = $event"
					:agents
					:artifacts
				/>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { NTabs, NTabPane } from "naive-ui"
import ArtifactsList from "@/components/artifacts/ArtifactsList.vue"
import ArtifactsCollect from "@/components/artifacts/ArtifactsCollect.vue"
import ArtifactsCommand from "@/components/artifacts/ArtifactsCommand.vue"
import ArtifactsQuarantine from "@/components/artifacts/ArtifactsQuarantine.vue"
import type { Artifact } from "@/types/artifacts.d"
import type { Agent } from "@/types/agents.d"

const artifacts = ref<Artifact[]>([])
const agents = ref<Agent[]>([])

const activeTab = ref<string | undefined>(undefined)
</script>

<style lang="scss" scoped></style>
