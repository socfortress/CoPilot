<template>
	<div class="patch-tuesday-detail">
		<!-- Header Section -->
		<div class="detail-header">
			<div class="header-row">
				<PatchTuesdayPriorityBadge :priority="item.prioritization.priority" />
				<n-tag v-if="item.kev.in_kev" type="error" size="small">
					<template #icon>
						<Icon :name="AlertIcon" />
					</template>
					Known Exploited
				</n-tag>
				<n-tag v-if="item.severity" :type="getSeverityType(item.severity)" size="small">
					{{ item.severity }}
				</n-tag>
			</div>
			<h2 class="detail-title">{{ item.title || "No title available" }}</h2>
		</div>

		<n-divider />

		<!-- Scores Section -->
		<div class="detail-section">
			<h3 class="section-title">Risk Scores</h3>
			<div class="scores-grid">
				<div v-if="item.cvss.base !== null" class="score-card">
					<span class="score-label">CVSS Base Score</span>
					<span class="score-value" :class="getCvssClass(item.cvss.base)">
						{{ item.cvss.base.toFixed(1) }}
					</span>
					<span v-if="item.cvss.vector" class="score-detail">{{ item.cvss.vector }}</span>
				</div>
				<div v-if="item.epss.score !== null" class="score-card">
					<span class="score-label">EPSS Score</span>
					<span class="score-value">{{ (item.epss.score * 100).toFixed(2) }}%</span>
					<span class="score-detail">Probability of exploitation</span>
				</div>
				<div v-if="item.epss.percentile !== null" class="score-card">
					<span class="score-label">EPSS Percentile</span>
					<span class="score-value">{{ (item.epss.percentile * 100).toFixed(0) }}%</span>
					<span class="score-detail">Higher than {{ (item.epss.percentile * 100).toFixed(0) }}% of CVEs</span>
				</div>
			</div>
		</div>

		<n-divider />

		<!-- Prioritization Section -->
		<div class="detail-section">
			<h3 class="section-title">Prioritization</h3>
			<n-alert :type="getPriorityAlertType(item.prioritization.priority)" class="mb-3">
				<template #header>{{ item.prioritization.suggested_sla }}</template>
			</n-alert>
			<div class="reasons-list">
				<strong>Priority Factors:</strong>
				<ul>
					<li v-for="reason in item.prioritization.reason" :key="reason">{{ reason }}</li>
				</ul>
			</div>
		</div>

		<n-divider />

		<!-- Affected Product Section -->
		<div class="detail-section">
			<h3 class="section-title">Affected Product</h3>
			<n-descriptions :column="1" label-placement="left" bordered size="small">
				<n-descriptions-item label="Product">
					{{ item.affected.product }}
				</n-descriptions-item>
				<n-descriptions-item label="Family">
					<n-tag size="small">{{ item.affected.family }}</n-tag>
				</n-descriptions-item>
			</n-descriptions>
		</div>

		<!-- KEV Details (if applicable) -->
		<template v-if="item.kev.in_kev">
			<n-divider />
			<div class="detail-section">
				<h3 class="section-title">
					<Icon :name="AlertIcon" class="text-error mr-2" />
					CISA KEV Details
				</h3>
				<n-alert type="error" class="mb-3">
					This vulnerability is in the CISA Known Exploited Vulnerabilities catalog and is actively being
					exploited in the wild.
				</n-alert>
				<n-descriptions :column="1" label-placement="left" bordered size="small">
					<n-descriptions-item v-if="item.kev.date_added" label="Date Added">
						{{ formatDate(item.kev.date_added) }}
					</n-descriptions-item>
					<n-descriptions-item v-if="item.kev.due_date" label="Remediation Due">
						<n-tag type="error" size="small">{{ formatDate(item.kev.due_date) }}</n-tag>
					</n-descriptions-item>
					<n-descriptions-item v-if="item.kev.required_action" label="Required Action">
						{{ item.kev.required_action }}
					</n-descriptions-item>
					<n-descriptions-item v-if="item.kev.known_ransomware_campaign_use" label="Ransomware Use">
						{{ item.kev.known_ransomware_campaign_use }}
					</n-descriptions-item>
					<n-descriptions-item v-if="item.kev.short_description" label="Description">
						{{ item.kev.short_description }}
					</n-descriptions-item>
				</n-descriptions>
			</div>
		</template>

		<n-divider />

		<!-- Remediation Section -->
		<div class="detail-section">
			<h3 class="section-title">Remediation</h3>
			<div v-if="item.remediation.kbs.length > 0" class="kb-list">
				<strong>Related KB Articles:</strong>
				<div class="kb-tags">
					<n-tag v-for="kb in item.remediation.kbs" :key="kb" size="small" class="kb-tag" @click="openKB(kb)">
						<template #icon>
							<Icon :name="ExternalLinkIcon" />
						</template>
						{{ kb }}
					</n-tag>
				</div>
			</div>
			<n-empty v-else description="No KB articles available" size="small" />
		</div>

		<n-divider />

		<!-- Source Section -->
		<div class="detail-section">
			<h3 class="section-title">Sources</h3>
			<div class="source-links">
				<n-button text tag="a" :href="item.source.msrc_cvrf_url" target="_blank" type="primary">
					<template #icon>
						<Icon :name="ExternalLinkIcon" />
					</template>
					MSRC Security Update
				</n-button>
				<n-button
					text
					tag="a"
					:href="`https://nvd.nist.gov/vuln/detail/${item.cve}`"
					target="_blank"
					type="primary"
				>
					<template #icon>
						<Icon :name="ExternalLinkIcon" />
					</template>
					NVD Entry
				</n-button>
			</div>
		</div>

		<!-- Metadata Footer -->
		<div class="detail-footer">
			<span>Cycle: {{ item.cycle }}</span>
			<span>•</span>
			<span>Updated: {{ formatDateTime(item.timestamp_utc) }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
// TODO: refactor
import type { PatchTuesdayItem } from "@/types/patchTuesday.d"
import { NAlert, NButton, NDescriptions, NDescriptionsItem, NDivider, NEmpty, NTag } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { PriorityLevel } from "@/types/patchTuesday.d"
import PatchTuesdayPriorityBadge from "./PatchTuesdayPriorityBadge.vue"

defineProps<{
	item: PatchTuesdayItem
}>()
const AlertIcon = "carbon:warning"
const ExternalLinkIcon = "carbon:launch"

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

function getPriorityAlertType(priority: PriorityLevel | string): "error" | "warning" | "info" | "success" {
	switch (priority) {
		case PriorityLevel.P0:
			return "error"
		case PriorityLevel.P1:
			return "warning"
		case PriorityLevel.P2:
			return "info"
		case PriorityLevel.P3:
			return "success"
		default:
			return "info"
	}
}

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
	return new Date(dateStr).toLocaleString()
}

function openKB(kb: string) {
	window.open(`https://support.microsoft.com/help/${kb.replace("KB", "")}`, "_blank")
}
</script>

<style scoped lang="scss">
.patch-tuesday-detail {
	.detail-header {
		.header-row {
			display: flex;
			gap: 8px;
			margin-bottom: 12px;
		}

		.detail-title {
			font-size: 1.1rem;
			font-weight: 600;
			line-height: 1.4;
		}
	}

	.detail-section {
		.section-title {
			font-size: 0.9rem;
			font-weight: 600;
			margin-bottom: 12px;
			display: flex;
			align-items: center;
		}
	}

	.scores-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 12px;

		.score-card {
			background: var(--bg-secondary-color);
			padding: 12px;
			border-radius: 8px;
			display: flex;
			flex-direction: column;

			.score-label {
				font-size: 0.75rem;
				opacity: 0.7;
				margin-bottom: 4px;
			}

			.score-value {
				font-size: 1.25rem;
				font-weight: 700;

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

			.score-detail {
				font-size: 0.7rem;
				opacity: 0.6;
				margin-top: 4px;
			}
		}
	}

	.reasons-list {
		ul {
			margin: 8px 0 0 20px;
			padding: 0;

			li {
				margin-bottom: 4px;
				font-size: 0.875rem;
			}
		}
	}

	.kb-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 8px;

		.kb-tag {
			cursor: pointer;

			&:hover {
				opacity: 0.8;
			}
		}
	}

	.source-links {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.detail-footer {
		margin-top: 24px;
		padding-top: 12px;
		border-top: 1px solid var(--border-color);
		font-size: 0.75rem;
		opacity: 0.6;
		display: flex;
		gap: 8px;
	}
}
</style>
