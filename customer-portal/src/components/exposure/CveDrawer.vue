<template>
	<n-drawer
		v-model:show="show"
		:width="560"
		placement="right"
		:auto-focus="false"
		data-testid="exposure-cve-drawer"
		class="max-w-[90vw]"
	>
		<n-drawer-content closable :native-scrollbar="false" body-content-class="flex flex-col gap-5">
			<template #header>
				<div class="flex min-w-0 flex-col gap-1">
					<span class="text-tertiary text-xxs font-medium tracking-[0.12em] uppercase">
						{{ $t("exposure.cve.heading") }}
					</span>
					<span class="text-default truncate font-mono text-base" data-testid="exposure-cve-id">
						{{ cveId }}
					</span>
				</div>
			</template>

			<div v-if="loading && !detail" class="flex flex-col gap-3" data-testid="exposure-cve-loading">
				<n-skeleton text :repeat="3" />
				<n-skeleton v-for="n of 3" :key="n" :height="40" :sharp="false" class="rounded-md" />
			</div>

			<n-alert v-else-if="failure" type="error" :bordered="false" data-testid="exposure-cve-error">
				{{ failure }}
			</n-alert>

			<template v-else-if="detail">
				<dl class="m-0 grid grid-cols-2 gap-x-6 gap-y-3 @md:grid-cols-4">
					<div class="flex min-w-0 flex-col gap-1">
						<dt :class="HEAD">{{ $t("common.fields.severity") }}</dt>
						<dd class="m-0">
							<span :class="[CHIP, severityClasses(detail.severity)]">
								{{
									detail.severity
										? severityText(detail.severity)
										: $t("exposure.vulnerabilities.unknownSeverity")
								}}
							</span>
						</dd>
					</div>
					<div class="flex min-w-0 flex-col gap-1">
						<dt :class="HEAD">CVSS</dt>
						<dd class="text-default m-0 font-mono text-sm tabular-nums">{{ formatCvss(detail.cvss) }}</dd>
					</div>
					<div
						class="flex min-w-0 flex-col gap-1"
						:title="$t('exposure.cve.epssTitle')"
					>
						<dt :class="HEAD">EPSS</dt>
						<dd class="text-default m-0 font-mono text-sm tabular-nums" data-testid="exposure-cve-epss">
							{{ formatEpss(detail.epss) }}
						</dd>
					</div>
					<div class="flex min-w-0 flex-col gap-1">
						<dt :class="HEAD">{{ $t("exposure.cve.published") }}</dt>
						<dd class="text-default m-0 font-mono text-xs">
							{{ detail.published ? formatDate(detail.published, dFormats.date, { tz: true }) : "—" }}
						</dd>
					</div>
				</dl>

				<p v-if="detail.description" class="text-secondary m-0 text-sm" data-testid="exposure-cve-description">
					{{ detail.description }}
				</p>

				<section class="flex flex-col gap-2">
					<h3 :class="HEAD" class="m-0">
						{{
							$t("exposure.cve.agentsHeading", {
								count: `${detail.agents.length.toLocaleString()}${detail.truncated ? "+" : ""}`
							})
						}}
					</h3>
					<p v-if="!detail.agents.length" class="text-tertiary m-0 text-sm" data-testid="exposure-cve-none">
						{{ $t("exposure.cve.none") }}
					</p>
					<ul
						v-else
						class="border-default divide-border m-0 flex list-none flex-col divide-y overflow-hidden rounded-lg border p-0"
					>
						<li
							v-for="agent of detail.agents"
							:key="`${agent.agent_id}-${agent.package}-${agent.version}`"
							data-testid="exposure-cve-agent"
						>
							<!-- The whole row opens the agent's vulnerabilities, searched for this CVE. -->
							<RouterLink
								:to="agentLink(agent.agent_id, { tab: 'vulnerabilities', search: cveId ?? '' })"
								class="group hover:bg-secondary/60 focus-visible:outline-primary flex items-center gap-3 px-3 py-2 no-underline transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2"
								data-testid="exposure-cve-agent-link"
								@click="show = false"
							>
								<span class="flex min-w-0 grow flex-col gap-0.5">
									<span
										class="text-default group-hover:text-primary truncate text-sm font-medium transition-colors"
									>
										<bdi>{{ agent.hostname }}</bdi>
									</span>
									<span class="text-tertiary truncate font-mono text-xs">
										<bdi>{{ [agent.package, agent.version].filter(Boolean).join(" ") || "—" }}</bdi>
									</span>
								</span>
								<span class="text-tertiary shrink-0 font-mono text-xs">
									{{ agent.detected ? formatDate(agent.detected, dFormats.date, { tz: true }) : "" }}
								</span>
								<Icon
									name="carbon:chevron-right"
									:size="14"
									class="text-tertiary group-hover:text-default shrink-0 transition-colors"
								/>
							</RouterLink>
						</li>
					</ul>
					<p v-if="detail.truncated" class="text-tertiary m-0 text-xs">
						{{ $t("exposure.cve.truncated") }}
					</p>
				</section>

				<section v-if="detail.references.length" class="flex min-w-0 flex-col gap-1.5">
					<h3 :class="HEAD" class="m-0">
						{{ $t("exposure.cve.references", { count: detail.references.length }) }}
					</h3>
					<template v-for="reference of detail.references" :key="reference">
						<a
							v-if="isWebLink(reference)"
							:href="reference"
							target="_blank"
							rel="noopener noreferrer"
							class="text-primary truncate font-mono text-xs hover:underline"
						>
							{{ reference }}
						</a>
						<span v-else class="text-secondary truncate font-mono text-xs">{{ reference }}</span>
					</template>
				</section>
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CveDetail } from "@/types/exposure"
import { NAlert, NDrawer, NDrawerContent, NSkeleton } from "naive-ui"
import { computed, ref, watch } from "vue"
import { RouterLink } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { i18nGlobal } from "@/lang"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { agentLink, formatCvss, formatEpss, isWebLink, severityClasses, severityText } from "./exposure"

/**
 * One CVE of the Exposure page (#1289): what Wazuh says of it, and the customer's agents it
 * affects, each a link to that agent's vulnerabilities searched for it. Loads when opened.
 */

const { cveId } = defineProps<{ cveId: string | null }>()
const show = defineModel<boolean>("show", { required: true })

const HEAD = "text-tertiary text-xxs font-medium tracking-[0.12em] uppercase"
const CHIP = "inline-flex rounded border px-1.5 py-0.5 text-xxs font-medium tracking-wide uppercase"

const dFormats = useSettingsStore().dateFormat
const customerFilterStore = useCustomerFilterStore()
const detail = ref<CveDetail | null>(null)
const error = ref<string | null>(null)
const { loading, run } = useLatestRequest()

const failure = computed(() => error.value || detail.value?.error || null)

function load(id: string) {
	detail.value = null
	error.value = null
	return run(
		async signal => {
			const response = await Api.exposure.getCve(id, customerFilterStore.queryCustomerCodes, signal)
			if (signal.aborted) return
			detail.value = response.data
		},
		err => {
			error.value = getApiErrorMessage(err as ApiError) || i18nGlobal.t("exposure.cve.loadFailed")
		}
	)
}

watch(
	() => [show.value, cveId] as const,
	([open, id]) => {
		if (open && id && detail.value?.cve_id !== id) load(id)
	},
	{ immediate: true }
)
</script>
