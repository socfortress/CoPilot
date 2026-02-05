<template>
    <n-card
        size="small"
        :bordered="false"
        hoverable
        class="patch-tuesday-card"
        :class="[`priority-${item.prioritization.priority.toLowerCase()}`]"
    >
        <!-- Header -->
        <div class="card-header">
            <div class="cve-info">
                <span class="cve-id">{{ item.cve }}</span>
                <PatchTuesdayPriorityBadge :priority="item.prioritization.priority" />
            </div>
            <div class="badges">
                <n-tag v-if="item.kev.in_kev" type="error" size="small" round>
                    <template #icon>
                        <Icon :name="AlertIcon" />
                    </template>
                    KEV
                </n-tag>
                <n-tag v-if="item.severity" :type="getSeverityType(item.severity)" size="small">
                    {{ item.severity }}
                </n-tag>
            </div>
        </div>

        <!-- Title -->
        <p class="card-title">{{ item.title || "No title available" }}</p>

        <!-- Product Info -->
        <div class="product-info">
            <n-tag size="small" :bordered="false">
                {{ item.affected.family }}
            </n-tag>
            <span class="product-name">{{ truncateProduct(item.affected.product) }}</span>
        </div>

        <!-- Scores Row -->
        <div class="scores-row">
            <div v-if="item.cvss.base !== null" class="score-item">
                <span class="score-label">CVSS</span>
                <span class="score-value" :class="getCvssClass(item.cvss.base)">
                    {{ item.cvss.base.toFixed(1) }}
                </span>
            </div>
            <div v-if="item.epss.score !== null" class="score-item">
                <span class="score-label">EPSS</span>
                <span class="score-value">{{ (item.epss.score * 100).toFixed(1) }}%</span>
            </div>
            <div v-if="item.epss.percentile !== null" class="score-item">
                <span class="score-label">Percentile</span>
                <span class="score-value">{{ (item.epss.percentile * 100).toFixed(0) }}%</span>
            </div>
        </div>

        <!-- KB Articles -->
        <div v-if="item.remediation.kbs.length > 0" class="kb-row">
            <Icon :name="LinkIcon" :size="14" />
            <span class="kb-list">{{ item.remediation.kbs.slice(0, 3).join(", ") }}</span>
            <span v-if="item.remediation.kbs.length > 3" class="kb-more">
                +{{ item.remediation.kbs.length - 3 }} more
            </span>
        </div>

        <!-- SLA Hint -->
        <div class="sla-hint">
            <Icon :name="ClockIcon" :size="14" />
            <span>{{ getSlaHint(item.prioritization.suggested_sla) }}</span>
        </div>
    </n-card>
</template>

<script setup lang="ts">
import { NCard, NTag } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import type { PatchTuesdayItem } from "@/types/patchTuesday.d"
import PatchTuesdayPriorityBadge from "./PatchTuesdayPriorityBadge.vue"

const AlertIcon = "carbon:warning"
const ClockIcon = "carbon:time"
const LinkIcon = "carbon:link"

defineProps<{
    item: PatchTuesdayItem
}>()

function getSeverityType(severity: string): "error" | "warning" | "info" | "default" {
    const s = severity.toLowerCase()
    if (s === "critical") return "error"
    if (s === "important") return "warning"
    if (s === "moderate") return "info"
    return "default"
}

function getCvssClass(score: number): string {
    if (score >= 9.0) return "critical"
    if (score >= 7.0) return "high"
    if (score >= 4.0) return "medium"
    return "low"
}

function truncateProduct(product: string): string {
    if (product.length <= 40) return product
    return product.substring(0, 40) + "..."
}

function getSlaHint(sla: string): string {
    if (sla.includes("immediately") || sla.includes("24h")) return "Patch immediately"
    if (sla.includes("72h")) return "Patch within 72 hours"
    if (sla.includes("7-14")) return "Patch within 7-14 days"
    return "Patch within 30 days"
}
</script>

<style scoped lang="scss">
.patch-tuesday-card {
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    border-left: 4px solid transparent;
    background: var(--bg-secondary-color);

    &.priority-p0 {
        border-left-color: #ef4444;
    }

    &.priority-p1 {
        border-left-color: #f97316;
    }

    &.priority-p2 {
        border-left-color: #eab308;
    }

    &.priority-p3 {
        border-left-color: #22c55e;
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;

        .cve-info {
            display: flex;
            align-items: center;
            gap: 8px;

            .cve-id {
                font-weight: 600;
                font-size: 0.95rem;
                font-family: monospace;
            }
        }

        .badges {
            display: flex;
            gap: 4px;
        }
    }

    .card-title {
        font-size: 0.875rem;
        line-height: 1.4;
        margin-bottom: 12px;
        opacity: 0.9;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .product-info {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;

        .product-name {
            font-size: 0.8rem;
            opacity: 0.7;
        }
    }

    .scores-row {
        display: flex;
        gap: 16px;
        margin-bottom: 12px;

        .score-item {
            display: flex;
            flex-direction: column;

            .score-label {
                font-size: 0.7rem;
                text-transform: uppercase;
                opacity: 0.6;
            }

            .score-value {
                font-weight: 600;
                font-size: 0.9rem;

                &.critical {
                    color: #ef4444;
                }
                &.high {
                    color: #f97316;
                }
                &.medium {
                    color: #eab308;
                }
                &.low {
                    color: #22c55e;
                }
            }
        }
    }

    .kb-row {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        opacity: 0.7;
        margin-bottom: 8px;

        .kb-more {
            opacity: 0.6;
        }
    }

    .sla-hint {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75rem;
        opacity: 0.6;
        padding-top: 8px;
        border-top: 1px solid var(--border-color);
    }
}
</style>
