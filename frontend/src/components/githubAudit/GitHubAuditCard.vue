<template>
    <n-card class="github-audit-card" hoverable @click="$emit('click', config)">
        <div class="flex justify-between items-start">
            <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                    <n-icon size="20" :color="config.enabled ? '#18a058' : '#999'">
                        <Icon :name="GithubIcon" />
                    </n-icon>
                    <h3 class="text-lg font-semibold m-0">{{ config.organization }}</h3>
                    <n-tag v-if="!config.enabled" type="warning" size="small">Disabled</n-tag>
                </div>

                <div class="text-secondary text-sm mb-3">
                    <span>Customer: {{ config.customer_code }}</span>
                </div>

                <div class="flex gap-4 text-sm">
                    <div v-if="config.last_audit_at" class="flex items-center gap-1">
                        <n-icon><Icon :name="ClockIcon" /></n-icon>
                        <span>Last audit: {{ formatDate(config.last_audit_at) }}</span>
                    </div>
                    <div v-if="config.last_audit_grade" class="flex items-center gap-1">
                        <span>Grade:</span>
                        <GitHubAuditGradeBadge :grade="config.last_audit_grade" :score="config.last_audit_score ?? undefined" />
                    </div>
                    <div v-if="config.auto_audit_enabled" class="flex items-center gap-1">
                        <n-icon color="#18a058"><Icon :name="ScheduleIcon" /></n-icon>
                        <span>Scheduled</span>
                    </div>
                </div>
            </div>

            <div class="flex flex-col gap-2">
                <n-button type="primary" size="small" :loading="running" @click.stop="runAudit">
                    <template #icon>
                        <n-icon><Icon :name="PlayIcon" /></n-icon>
                    </template>
                    Run Audit
                </n-button>
                <n-button size="small" @click.stop="$emit('edit', config)">
                    <template #icon>
                        <n-icon><Icon :name="EditIcon" /></n-icon>
                    </template>
                    Edit
                </n-button>
            </div>
        </div>

        <n-divider v-if="config.last_audit_score !== null" style="margin: 12px 0" />

        <div v-if="config.last_audit_score !== null" class="audit-score-bar">
            <div class="flex justify-between mb-1">
                <span class="text-sm">Security Score</span>
                <span class="text-sm font-semibold">{{ config.last_audit_score?.toFixed(1) }}%</span>
            </div>
            <n-progress
                type="line"
                :percentage="config.last_audit_score ?? 0"
                :status="scoreStatus"
                :show-indicator="false"
            />
        </div>
    </n-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { NButton, NCard, NDivider, NIcon, NProgress, NTag, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import GitHubAuditGradeBadge from "./GitHubAuditGradeBadge.vue"
import Api from "@/api"
import type { GitHubAuditConfig } from "@/types/githubAudit.d"
import { formatDate } from "@/utils"

const GithubIcon = "carbon:logo-github"
const ClockIcon = "carbon:time"
const ScheduleIcon = "carbon:calendar"
const PlayIcon = "carbon:play-filled"
const EditIcon = "carbon:edit"

const props = defineProps<{
    config: GitHubAuditConfig
}>()

const emit = defineEmits<{
    (e: "click", config: GitHubAuditConfig): void
    (e: "edit", config: GitHubAuditConfig): void
    (e: "audit-complete"): void
}>()

const message = useMessage()
const running = ref(false)

const scoreStatus = computed(() => {
    const score = props.config.last_audit_score ?? 0
    if (score >= 80) return "success"
    if (score >= 60) return "warning"
    return "error"
})

async function runAudit() {
    running.value = true
    try {
        await Api.githubAudit.runAuditFromConfig(props.config.id)
        message.success("Audit completed successfully")
        emit("audit-complete")
    } catch (error: any) {
        message.error(error.response?.data?.detail || "Failed to run audit")
    } finally {
        running.value = false
    }
}
</script>

<style scoped>
.github-audit-card {
    cursor: pointer;
    transition: all 0.2s ease;
}

.github-audit-card:hover {
    transform: translateY(-2px);
}

.text-secondary {
    color: var(--text-color-3);
}
</style>
