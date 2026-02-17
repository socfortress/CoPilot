<template>
	<div class="patch-tuesday-stats">
		<n-grid :x-gap="16" :y-gap="16" cols="1 s:2 m:4 l:5">
			<!-- Total CVEs -->
			<n-grid-item>
				<n-card size="small" :bordered="false" class="stat-card">
					<div class="stat-content">
						<div class="stat-icon total">
							<Icon :name="ShieldIcon" :size="24" />
						</div>
						<div class="stat-info">
							<span class="stat-value">{{ summary?.unique_cves ?? "-" }}</span>
							<span class="stat-label">Unique CVEs</span>
						</div>
					</div>
				</n-card>
			</n-grid-item>

			<!-- P0 Emergency -->
			<n-grid-item>
				<n-card size="small" :bordered="false" class="stat-card priority-p0">
					<div class="stat-content">
						<div class="stat-icon p0">
							<Icon :name="AlertIcon" :size="24" />
						</div>
						<div class="stat-info">
							<span class="stat-value">{{ summary?.by_priority?.P0 ?? 0 }}</span>
							<span class="stat-label">P0 Emergency</span>
						</div>
					</div>
				</n-card>
			</n-grid-item>

			<!-- P1 High -->
			<n-grid-item>
				<n-card size="small" :bordered="false" class="stat-card priority-p1">
					<div class="stat-content">
						<div class="stat-icon p1">
							<Icon :name="UrgentIcon" :size="24" />
						</div>
						<div class="stat-info">
							<span class="stat-value">{{ summary?.by_priority?.P1 ?? 0 }}</span>
							<span class="stat-label">P1 High</span>
						</div>
					</div>
				</n-card>
			</n-grid-item>

			<!-- P2 Medium -->
			<n-grid-item>
				<n-card size="small" :bordered="false" class="stat-card priority-p2">
					<div class="stat-content">
						<div class="stat-icon p2">
							<Icon :name="InfoIcon" :size="24" />
						</div>
						<div class="stat-info">
							<span class="stat-value">{{ summary?.by_priority?.P2 ?? 0 }}</span>
							<span class="stat-label">P2 Medium</span>
						</div>
					</div>
				</n-card>
			</n-grid-item>

			<!-- P3 Low -->
			<n-grid-item>
				<n-card size="small" :bordered="false" class="stat-card priority-p3">
					<div class="stat-content">
						<div class="stat-icon p3">
							<Icon :name="CheckIcon" :size="24" />
						</div>
						<div class="stat-info">
							<span class="stat-value">{{ summary?.by_priority?.P3 ?? 0 }}</span>
							<span class="stat-label">P3 Low</span>
						</div>
					</div>
				</n-card>
			</n-grid-item>
		</n-grid>

		<!-- Additional Info Bar -->
		<div v-if="summary" class="info-bar mt-4">
			<n-space :size="24">
				<span class="info-item">
					<Icon :name="CalendarIcon" class="mr-1" />
					Patch Tuesday:
					<strong>{{ formatDate(summary.patch_tuesday_date) }}</strong>
				</span>
				<span class="info-item">
					<Icon :name="DatabaseIcon" class="mr-1" />
					Total Records:
					<strong>{{ summary.total_records }}</strong>
				</span>
				<span class="info-item">
					<Icon :name="ClockIcon" class="mr-1" />
					Generated:
					<strong>{{ formatDateTime(summary.generated_utc) }}</strong>
				</span>
			</n-space>
		</div>
	</div>
</template>

<script setup lang="ts">
// TODO: refactor
import type { PatchTuesdaySummary } from "@/types/patchTuesday.d"
import { NCard, NGrid, NGridItem, NSpace } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	summary: PatchTuesdaySummary | null
	loading?: boolean
}>()
const AlertIcon = "carbon:warning"
const CalendarIcon = "carbon:calendar"
const CheckIcon = "carbon:checkmark-filled"
const ClockIcon = "carbon:time"
const DatabaseIcon = "carbon:data-base"
const InfoIcon = "carbon:information"
const ShieldIcon = "carbon:security"
const UrgentIcon = "carbon:warning-hex"

function formatDate(dateStr: string): string {
	if (!dateStr) return "-"
	return new Date(dateStr).toLocaleDateString("en-US", {
		year: "numeric",
		month: "long",
		day: "numeric"
	})
}

function formatDateTime(dateStr: string): string {
	if (!dateStr) return "-"
	return new Date(dateStr).toLocaleString("en-US", {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit"
	})
}
</script>

<style scoped lang="scss">
.patch-tuesday-stats {
	.stat-card {
		border-radius: 8px;
		background: var(--bg-secondary-color);

		.stat-content {
			display: flex;
			align-items: center;
			gap: 12px;
		}

		.stat-icon {
			width: 48px;
			height: 48px;
			border-radius: 8px;
			display: flex;
			align-items: center;
			justify-content: center;

			&.total {
				background: rgba(99, 102, 241, 0.15);
				color: #6366f1;
			}

			&.p0 {
				background: rgba(239, 68, 68, 0.15);
				color: #ef4444;
			}

			&.p1 {
				background: rgba(249, 115, 22, 0.15);
				color: #f97316;
			}

			&.p2 {
				background: rgba(234, 179, 8, 0.15);
				color: #eab308;
			}

			&.p3 {
				background: rgba(34, 197, 94, 0.15);
				color: #22c55e;
			}
		}

		.stat-info {
			display: flex;
			flex-direction: column;

			.stat-value {
				font-size: 1.5rem;
				font-weight: 700;
				line-height: 1.2;
			}

			.stat-label {
				font-size: 0.75rem;
				opacity: 0.7;
				text-transform: uppercase;
				letter-spacing: 0.5px;
			}
		}
	}

	.info-bar {
		padding: 12px 16px;
		background: var(--bg-secondary-color);
		border-radius: 8px;

		.info-item {
			display: inline-flex;
			align-items: center;
			font-size: 0.875rem;
			opacity: 0.8;
		}
	}
}
</style>
