<template>
	<n-button :size :type @click="goToGitHubAudit">
		<template #icon>
			<Icon :name="GitHubIcon" />
		</template>
		GitHub Audit
	</n-button>
</template>

<script setup lang="ts">
import type { Size, Type } from "naive-ui/es/button/src/interface"
import { NButton } from "naive-ui"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	size?: Size
	type?: Type
}>()

const GitHubIcon = "carbon:logo-github"
const router = useRouter()

function goToGitHubAudit() {
	router.push({ name: "GitHubAudit" })
}
</script>
