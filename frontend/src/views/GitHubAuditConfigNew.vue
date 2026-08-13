<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="New GitHub Audit Configuration" :back-route="routeGitHubAuditConfig()" />

		<GitHubAuditConfigForm @saved="onSaved()" @cancel="goBack(routeGitHubAuditConfig())" />
	</div>
</template>

<script setup lang="ts">
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import GitHubAuditConfigForm from "@/components/githubAudit/GitHubAuditConfigForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const { goBack, routeGitHubAuditConfig } = useNavigation()

function onSaved() {
	// land back on the audit list, which reloads its configs on mount
	routeGitHubAuditConfig().navigate()
}
</script>
