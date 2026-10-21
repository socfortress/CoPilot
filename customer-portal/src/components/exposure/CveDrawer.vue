<template>
	<n-drawer v-model:show="show" :width="560" placement="right" :auto-focus="false" data-testid="exposure-cve-drawer">
		<n-drawer-content closable :native-scrollbar="false" body-content-class="flex flex-col gap-5">
			<template #header>
				<div class="flex min-w-0 flex-col gap-1">
					<span class="text-tertiary text-xxs font-medium tracking-[0.12em] uppercase">Vulnerability</span>
					<span class="text-default truncate font-mono text-base" data-testid="exposure-cve-id">{{ cveId }}</span>
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
						<dt :class="HEAD">Severity</dt>
						<dd class="m-0">
							<span :class="[CHIP, severityClasses(detail.severity)]">{{ detail.severity ?? "unknown" }}</span>
						</dd>
					</div>
					<div class="flex min-w-0 flex-col gap-1">
						<dt :class="HEAD">CVSS</dt>
						<dd class="text-default m-0 font-mono text-sm tabular-nums">{{ formatCvss(detail.cvss) }}</dd>
					</div>
					<div class="flex min-w-0 flex-col gap-1" title="The probability of exploitation in the next 30 days">
						<dt :class="HEAD">EPSS</dt>
						<dd class="text-default m-0 font-mono text-sm tabular-nums" data-testid="exposure-cve-epss">
							{{ formatEpss(detail.epss) }}
						</dd>
					</div>
					<div class="flex min-w-0 flex-col gap-1">
						<dt :class="HEAD">Published</dt>
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
						Your agents with it · {{ detail.agents.length.toLocaleString() }}{{ detail.truncated ? "+" : "" }}
					</h3>
					<p v-if="!detail.agents.length" class="text-tertiary m-0 text-sm" data-testid="exposure-cve-none">
						None of your agents has it any more.
					</p>
					<ul v-else class="border-default divide-border m-0 flex list-none flex-col divide-y rounded-lg border p-0">
						<li
							v-for="agent of detail.agents"
							:key="`${agent.agent_id}-${agent.package}-${agent.version}`"
							class="flex items-center gap-3 px-3 py-2"
							data-testid="exposure-cve-agent"
						>
							<div class="flex min-w-0 grow flex-col gap-0.5">
								<RouterLink
									:to="agentLink(agent.agent_id, { tab: 'vulnerabilities', search: cveId ?? '' })"
									class="text-default hover:text-primary truncate text-sm font-medium no-underline transition-colors"
									data-testid="exposure-cve-agent-link"
									@click="show = false"
								>
									<bdi>{{ agent.hostname }}</bdi>
								</RouterLink>
								<span class="text-tertiary truncate font-mono text-xs">
									<bdi>{{ [agent.package, agent.version].filter(Boolean).join(" ") || "—" }}</bdi>
								</span>
							</div>
							<span class="text-tertiary shrink-0 font-mono text-xs">
								{{ agent.detected ? formatDate(agent.detected, dFormats.date, { tz: true }) : "" }}
							</span>
						</li>
					</ul>
					<p v-if="detail.truncated" class="text-tertiary m-0 text-xs">
						Only the first 1,000 are listed; the CSV export has them all.
					</p>
				</section>

				<section v-if="detail.references.length" class="flex min-w-0 flex-col gap-1.5">
					<h3 :class="HEAD" class="m-0">References · {{ detail.references.length }}</h3>
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
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { agentLink, formatCvss, formatEpss, isWebLink, severityClasses } from "./exposure"

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
			error.value = getApiErrorMessage(err as ApiError) || "Could not load the vulnerability."
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
