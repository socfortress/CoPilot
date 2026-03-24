<template>
	<n-button :size :type :secondary @click="goToGitHubAudit">
		<template #icon>
			<Icon :name="GitHubIcon" />
		</template>
		GitHub Audit
	</n-button>
</template>

<script setup lang="ts">
import type { ButtonSize, ButtonType } from "naive-ui"
import { NButton } from "naive-ui"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	size?: ButtonSize
	type?: ButtonType
	secondary?: boolean
}>()

const GitHubIcon = "carbon:logo-github"
const router = useRouter()

function goToGitHubAudit() {
	router.push({ name: "GitHubAudit" })
}
</script>
