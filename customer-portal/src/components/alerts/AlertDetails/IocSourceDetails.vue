<template>
	<div class="tid" data-testid="ioc-ti-details">
		<section
			v-for="result of found"
			:key="result.source"
			class="tid-panel"
			:data-source="result.source"
			data-testid="ioc-ti-details-source"
		>
			<header class="tid-head">
				<h4 class="tid-title">{{ sourceLabel(result.source) }}</h4>
				<a
					v-if="result.virustotal && virusTotalLink(result.virustotal.link)"
					:href="virusTotalLink(result.virustotal.link) ?? undefined"
					target="_blank"
					rel="noopener noreferrer"
					referrerpolicy="no-referrer"
					class="tid-link"
					data-testid="ioc-ti-vt-link"
				>
					{{ $t("iocEnrichment.virustotal.open") }}
					<Icon name="carbon:launch" :size="12" />
				</a>
			</header>

			<!-- Every fact on one grid: a fixed label column, the value beside it, a hairline between rows. -->
			<dl class="tid-rows">
				<template v-if="result.virustotal">
					<div v-if="result.virustotal.engines" class="tid-row" data-testid="ioc-ti-vt-engines">
						<dt>{{ $t("iocEnrichment.virustotal.engineCounts") }}</dt>
						<dd class="tid-counts">
							<span v-for="count of engineCounts(result.virustotal)" :key="count.key" class="tid-count">
								<span class="tid-count-value" :class="`tid-count-value--${count.key}`">{{ count.value }}</span>
								<span class="tid-count-label">{{ count.label }}</span>
							</span>
						</dd>
					</div>
					<div v-for="row of virusTotalRows(result.virustotal)" :key="row.label" class="tid-row">
						<dt>{{ row.label }}</dt>
						<dd :class="{ 'tid-mono': row.mono }">
							<bdi>{{ row.value }}</bdi>
						</dd>
					</div>
					<div v-if="result.virustotal.tags.length" class="tid-row" data-testid="ioc-ti-vt-tags">
						<dt>{{ $t("iocEnrichment.virustotal.tags") }}</dt>
						<dd class="tid-chips">
							<span v-for="tag of result.virustotal.tags" :key="tag" class="tid-chip">
								<bdi>{{ tag }}</bdi>
							</span>
						</dd>
					</div>
				</template>

				<template v-if="result.opencti">
					<div v-if="result.opencti.entity_types.length" class="tid-row">
						<dt>{{ $t("iocEnrichment.opencti.types") }}</dt>
						<dd>
							<bdi>{{ result.opencti.entity_types.join(", ") }}</bdi>
						</dd>
					</div>
					<div v-if="result.opencti.labels.length" class="tid-row" data-testid="ioc-ti-cti-labels">
						<dt>{{ $t("iocEnrichment.opencti.labels") }}</dt>
						<dd class="tid-chips">
							<span v-for="label of result.opencti.labels" :key="label" class="tid-chip">
								<bdi>{{ label }}</bdi>
							</span>
						</dd>
					</div>
					<div v-if="result.opencti.indicators.length" class="tid-row" data-testid="ioc-ti-cti-indicators">
						<dt>{{ $t("iocEnrichment.opencti.indicators") }}</dt>
						<dd>
							<ul class="tid-list">
								<li
									v-for="(indicator, index) of result.opencti.indicators"
									:key="index"
									:class="{ 'tid-item--revoked': indicator.revoked }"
								>
									<bdi class="tid-item-name">{{ indicator.name || "—" }}</bdi>
									<span class="tid-item-meta">
										<span v-if="indicator.revoked">{{ $t("iocEnrichment.opencti.revoked") }}</span>
										<span v-else-if="indicator.valid_until">
											{{ $t("iocEnrichment.opencti.validUntil", { date: day(indicator.valid_until) }) }}
										</span>
										<span v-if="indicator.score !== null" class="tid-score">{{ indicator.score }}</span>
									</span>
								</li>
							</ul>
						</dd>
					</div>
					<div v-if="result.opencti.reports.length" class="tid-row" data-testid="ioc-ti-cti-reports">
						<dt>{{ $t("iocEnrichment.opencti.reports") }}</dt>
						<dd>
							<ul class="tid-list">
								<li v-for="(report, index) of result.opencti.reports" :key="index">
									<bdi class="tid-item-name">{{ report.name }}</bdi>
									<span v-if="report.published" class="tid-item-meta">{{ day(report.published) }}</span>
								</li>
							</ul>
						</dd>
					</div>
				</template>
			</dl>

			<p v-if="result.opencti?.withheld" class="tid-withheld" data-testid="ioc-ti-cti-withheld">
				<Icon name="carbon:locked" :size="12" />
				<span>
					{{ $t("iocEnrichment.opencti.withheld", { count: result.opencti.withheld }, result.opencti.withheld) }}
				</span>
			</p>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { IocEnrichment, VirusTotalDetails } from "@/types/iocEnrichment"
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { sourceLabel, virusTotalLink } from "./iocEnrichment"

/**
 * The details each source gave about one IOC (#1318), a panel per source, side by side when there
 * is room. One layout for both: a header (the source, and VirusTotal's page), then rows of label
 * and value on one grid. Nothing the tile above already says is repeated. Text only.
 */

const { ioc } = defineProps<{
	ioc: IocEnrichment
}>()

const { t } = useI18n()
const dFormats = useSettingsStore().dateFormat

const found = computed(() => ioc.sources.filter(result => result.status === "found" && (result.virustotal || result.opencti)))

function day(date: string) {
	return formatDate(date, dFormats.date, { tz: true })
}

function engineCounts(details: VirusTotalDetails) {
	return (["malicious", "suspicious", "harmless", "undetected"] as const).map(key => ({
		key,
		value: details[key],
		label: t(`iocEnrichment.virustotal.${key}`)
	}))
}

function virusTotalRows(details: VirusTotalDetails) {
	const rows: { label: string; value: string; mono?: boolean }[] = []
	if (details.reputation !== null) {
		rows.push({ label: t("iocEnrichment.virustotal.reputation"), value: String(details.reputation), mono: true })
	}
	if (details.country) rows.push({ label: t("iocEnrichment.virustotal.country"), value: details.country, mono: true })
	if (details.as_owner) rows.push({ label: t("iocEnrichment.virustotal.asOwner"), value: details.as_owner })
	if (details.type_description) rows.push({ label: t("iocEnrichment.virustotal.fileType"), value: details.type_description })
	if (details.last_analysis_at) {
		rows.push({
			label: t("iocEnrichment.virustotal.lastAnalysis"),
			value: String(formatDate(details.last_analysis_at, dFormats.datetime, { tz: true })),
			mono: true
		})
	}
	return rows
}
</script>

<style scoped lang="scss">
// Labels in the theme's secondary ink, values in its full ink: never the tertiary, unreadable on
// the dark surface. One grid for every row, so labels and values line up down the panel.
.tid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
	// Side by side, the panels share one height; stacked on a phone, each keeps its own.
	align-items: stretch;
	gap: 8px;
}

.tid-panel {
	display: flex;
	flex-direction: column;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background: var(--bg-default-color);
	font-size: 13px;
}

.tid-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 10px 14px;
	border-bottom: 1px solid var(--border-color);
}

.tid-title {
	margin: 0;
	color: var(--fg-default-color);
	font-family: var(--font-family-mono);
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.1em;
	text-transform: uppercase;
}

.tid-link {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	color: var(--primary-color);
	font-size: 12px;
	text-decoration: none;

	&:hover {
		text-decoration: underline;
	}
}

.tid-rows {
	margin: 0;
	padding: 0 14px;
}

.tid-row {
	display: grid;
	grid-template-columns: 10.5rem minmax(0, 1fr);
	align-items: baseline;
	gap: 12px;
	padding: 9px 0;

	& + & {
		border-top: 1px solid var(--border-color);
	}

	dt {
		color: var(--fg-secondary-color);
		font-family: var(--font-family-mono);
		font-size: 11px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	dd {
		margin: 0;
		color: var(--fg-default-color);
		overflow-wrap: anywhere;
	}
}

.tid-mono {
	font-family: var(--font-family-mono);
	font-variant-numeric: tabular-nums;
}

// VirusTotal's engines: four figures in a row, each over its word.
.tid-counts {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 8px;
}

.tid-count {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.tid-count-value {
	color: var(--fg-default-color);
	font-family: var(--font-family-mono);
	font-size: 15px;
	font-weight: 600;
	font-variant-numeric: tabular-nums;
	line-height: 1.2;

	&--malicious {
		color: color-mix(in srgb, var(--error-color) 70%, var(--fg-default-color));
	}
	&--suspicious {
		color: color-mix(in srgb, var(--warning-color) 70%, var(--fg-default-color));
	}
}

.tid-count-label {
	color: var(--fg-secondary-color);
	font-size: 11px;
}

.tid-chips {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
}

.tid-chip {
	padding: 1px 7px;
	border: 1px solid var(--border-color);
	border-radius: 4px;
	color: var(--fg-default-color);
	font-family: var(--font-family-mono);
	font-size: 12px;
}

.tid-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	margin: 0;
	padding: 0;
	list-style: none;

	li {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 12px;
	}
}

.tid-item-name {
	min-width: 0;
	color: var(--fg-default-color);
}

.tid-item--revoked .tid-item-name {
	color: var(--fg-secondary-color);
	text-decoration: line-through;
}

.tid-item-meta {
	display: inline-flex;
	flex-shrink: 0;
	align-items: baseline;
	gap: 8px;
	color: var(--fg-secondary-color);
	font-family: var(--font-family-mono);
	font-size: 12px;
	font-variant-numeric: tabular-nums;
}

.tid-score {
	min-width: 28px;
	padding: 0 5px;
	border-radius: 3px;
	background: rgba(var(--fg-secondary-color-rgb) / 0.18);
	color: var(--fg-default-color);
	text-align: center;
}

.tid-withheld {
	display: flex;
	align-items: center;
	gap: 6px;
	// The panel's footer: at its bottom when the other panel is taller.
	margin: auto 0 0;
	padding: 9px 14px;
	border-top: 1px solid var(--border-color);
	color: var(--fg-secondary-color);
	font-size: 12px;
}
</style>
