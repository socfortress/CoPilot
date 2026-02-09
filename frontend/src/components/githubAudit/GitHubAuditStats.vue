<template>
    <div class="github-audit-stats">
        <n-grid :cols="4" :x-gap="16" :y-gap="16">
            <n-gi>
                <n-statistic label="Total Configs" :value="stats.totalConfigs" />
            </n-gi>
            <n-gi>
                <n-statistic label="Active Configs" :value="stats.activeConfigs" />
            </n-gi>
            <n-gi>
                <n-statistic label="Total Reports" :value="stats.totalReports" />
            </n-gi>
            <n-gi>
                <n-statistic label="Avg Score">
                    <template #default>
                        <span :class="scoreClass">{{ stats.avgScore.toFixed(1) }}%</span>
                    </template>
                </n-statistic>
            </n-gi>
        </n-grid>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { NGi, NGrid, NStatistic } from "naive-ui"

const props = defineProps<{
    stats: {
        totalConfigs: number
        activeConfigs: number
        totalReports: number
        avgScore: number
    }
}>()

const scoreClass = computed(() => {
    if (props.stats.avgScore >= 80) return "text-success"
    if (props.stats.avgScore >= 60) return "text-warning"
    return "text-error"
})
</script>

<style scoped>
.text-success {
    color: var(--success-color);
}
.text-warning {
    color: var(--warning-color);
}
.text-error {
    color: var(--error-color);
}
</style>
