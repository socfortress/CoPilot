<template>
    <n-button :size="size" :type="type" @click="goToGitHubAudit">
        <template #icon>
            <Icon :name="GitHubIcon" />
        </template>
        GitHub Audit
    </n-button>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

defineProps<{
    size?: "tiny" | "small" | "medium" | "large"
    type?: "default" | "primary" | "info" | "success" | "warning" | "error"
}>()

const GitHubIcon = "carbon:logo-github"
const router = useRouter()

function goToGitHubAudit() {
    router.push({ name: "GitHubAudit" })
}
</script>
