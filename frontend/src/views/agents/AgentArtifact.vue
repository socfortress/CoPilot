<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="artifact?.artifact_name" :back-route="routeAgent(agentId ?? undefined)">
			<template v-if="artifact" #meta>
				<span class="text-secondary font-mono text-sm">#{{ artifact.id }}</span>
			</template>
			<template #actions>
				<n-button
					v-if="artifact"
					class="shrink-0"
					size="small"
					secondary
					:loading="downloading"
					@click="downloadArtifact()"
				>
					<template #icon>
						<Icon :name="DownloadIcon" :size="14" />
					</template>
					Download
				</n-button>
			</template>
		</DetailPageHeader>

		<n-spin v-if="agentId && artifactId != null" :show="loading" class="min-h-40">
			<ArtifactDetails v-if="artifact" :artifact />
			<n-empty v-else-if="!loading" description="Artifact not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid artifact" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AgentArtifactData } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import ArtifactDetails from "@/components/agents/dataStore/ArtifactDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import Icon from "@/components/common/Icon.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteIdParam, useRouteParam } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const { routeAgent } = useNavigation()

const DownloadIcon = "carbon:download"

const message = useMessage()
const downloading = ref(false)

const agentId = useRouteParam("id")
const artifactId = useRouteIdParam("artifactId")

const { loading, entity: artifact } = useEntityDetails<AgentArtifactData, string>({
	entity: () => null,
	id: () => (agentId.value && artifactId.value != null ? `${agentId.value}|${artifactId.value}` : null),
	fetch: (_id, signal) =>
		Api.agents.getAgentArtifactDetails(agentId.value as string, artifactId.value as number, signal).then(res => ({
			entity: res.data.success ? (res.data.data ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Artifact not found",
	errorMessage: "An error occurred. Please try again later."
})

function downloadArtifact() {
	if (!artifact.value) return

	const file = artifact.value
	downloading.value = true
	message.loading(`Downloading ${file.file_name}...`)

	Api.agents
		.downloadAgentArtifact(agentId.value as string, file.id)
		.then(res => {
			saveAs(res.data, file.file_name)
			message.success(`Downloaded ${file.file_name}`)
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to download artifact")
		})
		.finally(() => {
			downloading.value = false
		})
}
</script>
