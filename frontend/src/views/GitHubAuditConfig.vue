<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="config?.organization" :back-route="routeGitHubAuditConfig()">
			<template v-if="config" #meta>
				<span class="text-secondary font-mono text-sm">#{{ config.id }}</span>
				<n-tag v-if="!config.enabled" type="warning" size="small">Disabled</n-tag>
			</template>
		</DetailPageHeader>

		<n-spin v-if="configId != null" :show="loading" class="min-h-40">
			<GitHubAuditDetail
				v-if="config"
				:config
				@updated="reload()"
				@edit="showEdit = true"
				@close="goBack(routeGitHubAuditConfig())"
			/>
			<n-empty v-else-if="!loading" description="Configuration not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid configuration" class="h-48 justify-center" />

		<!-- Edit drawer (self-contained, like the card) -->
		<n-drawer v-model:show="showEdit" :width="600" placement="right" class="max-w-[98vw]" display-directive="show">
			<n-drawer-content title="Edit Configuration" closable :native-scrollbar="false">
				<GitHubAuditConfigForm v-if="showEdit && config" :config @saved="onSaved()" @cancel="showEdit = false" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { GitHubAuditConfig } from "@/types/github-audit"
import { NDrawer, NDrawerContent, NEmpty, NSpin, NTag } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import GitHubAuditConfigForm from "@/components/githubAudit/GitHubAuditConfigForm.vue"
import GitHubAuditDetail from "@/components/githubAudit/GitHubAuditDetail.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeGitHubAuditConfig } = useNavigation()

const showEdit = ref(false)

const configId = useRouteIdParam("configId")

const {
	loading,
	entity: config,
	reload
} = useEntityDetails<GitHubAuditConfig, number>({
	entity: () => null,
	id: () => configId.value,
	// this endpoint's response carries the config directly (no success/message envelope)
	fetch: (id, signal) => Api.githubAudit.getConfig(id, signal).then(res => ({ entity: res.data.config ?? null })),
	notFoundMessage: "Configuration not found",
	errorMessage: "An error occurred. Please try again later."
})

function onSaved() {
	showEdit.value = false
	reload()
}
</script>
