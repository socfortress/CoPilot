<template>
	<section
		class="ti"
		:class="`ti--${toneOf(verdict)}`"
		data-testid="ioc-ti"
		:data-ioc="ioc.ioc_id"
		:aria-label="$t('iocEnrichment.title')"
	>
		<!-- 1. The verdict, then when it was given, then what the user can do. -->
		<header class="ti-head">
			<div class="ti-verdict" data-testid="ioc-ti-verdict" :data-verdict="verdict">
				<Icon :name="VERDICT_META[verdict].icon" :size="14" class="ti-verdict-icon" />
				<span class="ti-verdict-word">{{ verdictLabel(verdict) }}</span>
			</div>

			<div class="ti-meta">
				<span v-if="ioc.checked_at" data-testid="ioc-ti-checked">
					{{ $t("iocEnrichment.checkedAt", { date: when(ioc.checked_at) }) }}
				</span>
				<span v-if="!ioc.can_check && ioc.next_check_at" data-testid="ioc-ti-next">
					{{ $t("iocEnrichment.nextCheckAt", { date: when(ioc.next_check_at) }) }}
				</span>
			</div>

			<div class="ti-actions">
				<n-button
					v-if="hasDetails(ioc)"
					text
					size="tiny"
					:aria-expanded="open"
					class="ti-toggle"
					data-testid="ioc-ti-toggle"
					@click="open = !open"
				>
					{{ open ? $t("iocEnrichment.hideDetails") : $t("iocEnrichment.showDetails") }}
					<Icon :name="open ? 'carbon:chevron-up' : 'carbon:chevron-down'" :size="12" class="ml-1" />
				</n-button>
				<n-button
					v-if="ioc.can_check"
					size="tiny"
					:type="ioc.checked_at ? 'default' : 'primary'"
					:secondary="!ioc.checked_at"
					:loading="checking"
					:disabled="checking"
					:title="$t('iocEnrichment.checkHint')"
					data-testid="ioc-ti-check"
					@click="check()"
				>
					<template #icon>
						<Icon name="carbon:search" />
					</template>
					{{ ioc.checked_at ? $t("iocEnrichment.checkAgain") : $t("iocEnrichment.check") }}
				</n-button>
			</div>
		</header>

		<p v-if="note" class="ti-note" data-testid="ioc-ti-kind">{{ note }}</p>

		<p v-if="failure" class="ti-failure" role="alert" data-testid="ioc-ti-failure">
			<Icon name="carbon:warning-alt" :size="12" />
			<span>{{ failure }}</span>
		</p>

		<!-- 2. One tile per source: its verdict and the figure behind it. -->
		<ul v-if="!note && shown.length" class="ti-sources" data-testid="ioc-ti-sources">
			<li
				v-for="result of shown"
				:key="result.source"
				class="ti-source"
				:class="`ti-source--${result.status === 'found' ? toneOf(result.verdict) : 'neutral'}`"
				data-testid="ioc-ti-source"
				:data-source="result.source"
				:data-status="result.status"
			>
				<span class="ti-source-name">{{ sourceLabel(result.source) }}</span>{{ " " }}

				<template v-if="result.status === 'found' && result.verdict">
					<span class="ti-source-verdict">{{ verdictLabel(result.verdict) }}</span>{{ " " }}

					<template v-if="result.virustotal">
						<span
							v-if="result.virustotal.engines"
							class="ti-meter"
							role="img"
							:aria-label="engines(result.virustotal)"
						>
							<span
								v-for="segment of engineSegments(result.virustotal)"
								:key="segment.key"
								class="ti-meter-part"
								:class="`ti-meter-part--${segment.key}`"
								:style="{ width: `${segment.percent}%` }"
							/>
						</span>
						<span class="ti-source-figure">{{ engines(result.virustotal) }}</span>
					</template>

					<template v-if="result.opencti">
						<span
							v-if="result.opencti.score !== null"
							class="ti-meter ti-meter--score"
							role="img"
							:aria-label="`${$t('iocEnrichment.opencti.score')} ${result.opencti.score}`"
						>
							<span class="ti-meter-fill" :style="{ width: `${result.opencti.score}%` }" />
						</span>
						<span class="ti-source-figure">
							{{
								result.opencti.score !== null
									? `${$t("iocEnrichment.opencti.score")} ${result.opencti.score}`
									: $t("iocEnrichment.opencti.noScore")
							}}
						</span>
					</template>
				</template>

				<span v-else class="ti-source-status" :class="{ 'ti-source-status--error': result.status === 'error' }">
					{{ hasAnswer(result) ? verdictLabel("not_found") : sourceStatusText(result) }}
				</span>

				<span
					v-if="hasAnswer(result) && result.error && result.checked_at"
					class="ti-source-status ti-source-status--error"
					data-testid="ioc-ti-refresh-failed"
				>
					{{ $t("iocEnrichment.errors.refreshFailed", { date: when(result.checked_at) }) }}
				</span>
			</li>
		</ul>

		<!-- 3. What each source said in full, on request. -->
		<IocSourceDetails v-if="open" :ioc />
	</section>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { IocEnrichment, VirusTotalDetails } from "@/types/iocEnrichment"
import { NButton, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import {
	checkFailureMessage,
	engineSegments,
	enginesFlagged,
	hasAnswer,
	hasDetails,
	kindNote,
	sourceLabel,
	sourceStatusText,
	toneOf,
	VERDICT_META,
	verdictKey,
	verdictLabel
} from "./iocEnrichment"
import IocSourceDetails from "./IocSourceDetails.vue"

/**
 * What the SOC's Threat Intel says about one IOC of the alert (#1318), read in three levels: the
 * verdict (its colour on the left edge, its word first), a tile per source with the figure behind
 * its answer, then the details on request. Check is offered only when a source can be asked.
 * Every value from a source is shown as text.
 */

const { alertId, ioc } = defineProps<{
	alertId: number
	ioc: IocEnrichment
}>()

const emit = defineEmits<{ updated: [ioc: IocEnrichment] }>()

const message = useMessage()
const { t } = useI18n()
const dFormats = useSettingsStore().dateFormat

const checking = ref(false)
const failure = ref<string | null>(null)
const open = ref(false)

const verdict = computed(() => verdictKey(ioc))
const note = computed(() => kindNote(ioc.kind))
// A source this deployment can't ask says nothing useful to the customer.
const shown = computed(() => ioc.sources.filter(result => result.status !== "not_configured"))

function when(date: string) {
	return formatDate(date, dFormats.datetime, { tz: true })
}

function engines(details: VirusTotalDetails) {
	return details.engines
		? t("iocEnrichment.virustotal.engines", { flagged: enginesFlagged(details), engines: details.engines })
		: t("iocEnrichment.virustotal.noEngines")
}

async function check() {
	checking.value = true
	failure.value = null
	try {
		const res = await Api.iocEnrichment.check(alertId, ioc.ioc_id)
		emit("updated", res.data.ioc)
		message.success(t("iocEnrichment.checked"))
	} catch (err) {
		failure.value = checkFailureMessage(err as ApiError)
	} finally {
		checking.value = false
	}
}
</script>

<style scoped lang="scss">
// Text is the theme's full ink or its secondary ink, never the tertiary: on the dark surface the
// tertiary is about 3.5:1, unreadable at these sizes. Colour marks the verdict and nothing else.
.ti {
	--ti-accent: var(--fg-secondary-color);
	--ti-accent-rgb: var(--fg-secondary-color-rgb);
	display: flex;
	flex-direction: column;
	gap: 10px;
	margin-top: 4px;
	padding: 12px;
	border: 1px solid var(--border-color);
	border-radius: 8px;
	background: var(--bg-secondary-color);

	@each $tone in error, warning, info, success {
		&.ti--#{$tone} {
			--ti-accent: var(--#{$tone}-color);
			--ti-accent-rgb: var(--#{$tone}-color-rgb);
		}
	}
}

.ti-head {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px 14px;
}

.ti-verdict {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 2px 10px 2px 8px;
	border: 1px solid rgba(var(--ti-accent-rgb) / 0.45);
	border-radius: 999px;
	background: rgba(var(--ti-accent-rgb) / 0.14);
	// Mixed with the theme's ink: brighter on the dark surface, darker on the light one.
	color: color-mix(in srgb, var(--ti-accent) 70%, var(--fg-default-color));
	font-size: 13px;
	font-weight: 600;
	line-height: 20px;
}

.ti--neutral .ti-verdict {
	color: var(--fg-default-color);
}

.ti-meta {
	display: flex;
	flex-wrap: wrap;
	gap: 2px 14px;
	color: var(--fg-secondary-color);
	font-family: var(--font-family-mono);
	font-size: 12px;
	font-variant-numeric: tabular-nums;
}

.ti-actions {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-left: auto;
}

.ti-toggle {
	font-size: 12px;
}

.ti-note,
.ti-failure {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 0;
	color: var(--fg-default-color);
	font-size: 13px;
}

.ti-failure {
	color: color-mix(in srgb, var(--warning-color) 70%, var(--fg-default-color));
}

// Tiles side by side when there is room, stacked on a phone.
.ti-sources {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
	gap: 8px;
	margin: 0;
	padding: 0;
	list-style: none;
}

.ti-source {
	--tile-rgb: var(--fg-secondary-color-rgb);
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	align-items: baseline;
	gap: 8px 12px;
	padding: 10px 12px;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background: var(--bg-default-color);

	@each $tone in error, warning, info, success {
		&.ti-source--#{$tone} {
			--tile-rgb: var(--#{$tone}-color-rgb);
		}
	}
}

.ti-source-name {
	color: var(--fg-secondary-color);
	font-family: var(--font-family-mono);
	font-size: 11px;
	font-weight: 500;
	letter-spacing: 0.1em;
	text-transform: uppercase;
}

.ti-source-verdict {
	justify-self: end;
	color: color-mix(in srgb, rgb(var(--tile-rgb)) 70%, var(--fg-default-color));
	font-size: 13px;
	font-weight: 600;
}

.ti-source-status {
	grid-column: 1 / -1;
	color: var(--fg-default-color);
	font-size: 13px;

	&--error {
		color: color-mix(in srgb, var(--warning-color) 70%, var(--fg-default-color));
	}
}

.ti-source-figure {
	grid-column: 1 / -1;
	color: var(--fg-default-color);
	font-family: var(--font-family-mono);
	font-size: 12px;
	font-variant-numeric: tabular-nums;
}

// A thin bar: VirusTotal's engines by answer, or OpenCTI's score out of 100.
.ti-meter {
	position: relative;
	grid-column: 1 / -1;
	display: flex;
	height: 4px;
	overflow: hidden;
	border-radius: 2px;
	background: rgba(var(--fg-secondary-color-rgb) / 0.2);
	gap: 1px;
}

.ti-meter-part {
	height: 100%;
	min-width: 2px;

	// Only what flagged it is coloured: the engines that found nothing are the bar's grey body.
	&--malicious {
		background: var(--error-color);
	}
	&--suspicious {
		background: var(--warning-color);
	}
	&--harmless {
		background: rgba(var(--fg-secondary-color-rgb) / 0.55);
	}
	&--undetected {
		background: rgba(var(--fg-secondary-color-rgb) / 0.3);
	}
}

.ti-meter-fill {
	height: 100%;
	border-radius: 2px;
	background: rgb(var(--tile-rgb));
}
</style>
