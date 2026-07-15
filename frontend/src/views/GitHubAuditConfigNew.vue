<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeGitHubAuditConfig())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<span class="truncate text-lg font-semibold">New GitHub Audit Configuration</span>
		</div>

		<GitHubAuditConfigForm @saved="onSaved()" @cancel="goBack(routeGitHubAuditConfig())" />
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import GitHubAuditConfigForm from "@/components/githubAudit/GitHubAuditConfigForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const { goBack, routeGitHubAuditConfig } = useNavigation()

const BackIcon = "carbon:arrow-left"

function onSaved() {
	// land back on the audit list, which reloads its configs on mount
	routeGitHubAuditConfig().navigate()
}
</script>
