<template>
	<div class="flex flex-col gap-3" data-testid="exposure-compliance">
		<ExposureDisabled v-if="data && !data.enabled" />

		<template v-else>
			<div class="grid grid-cols-2 gap-3 @3xl:grid-cols-4" :aria-busy="loading || undefined">
				<article
					v-for="card of cards"
					:key="card.key"
					class="border-default bg-default flex min-w-0 flex-col gap-1.5 rounded-lg border px-3 py-2.5"
					:data-testid="`exposure-compliance-${card.key}`"
				>
					<span class="text-tertiary text-xxs truncate font-medium tracking-[0.12em] uppercase">
						{{ card.label }}
					</span>
					<span
						class="font-mono text-lg leading-none font-semibold tabular-nums"
						:class="known ? card.tone : 'text-tertiary'"
						data-testid="exposure-compliance-value"
					>
						{{ known ? card.value : "—" }}
					</span>
					<span class="text-tertiary text-xs text-pretty">{{ known ? card.caption : "" }}</span>
				</article>
			</div>

			<n-alert
				v-if="data?.unavailable_agents && !data.error"
				type="warning"
				:bordered="false"
				data-testid="exposure-compliance-unavailable"
			>
				Wazuh could not answer for {{ plural(data.unavailable_agents, "agent") }}: their results are missing
				from these figures.
			</n-alert>

			<n-alert v-if="failure" type="error" :bordered="false" data-testid="exposure-compliance-error">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<span>{{ failure }}</span>
					<n-button size="small" secondary @click="reload()">Try again</n-button>
				</div>
			</n-alert>

			<section
				v-else
				class="border-default bg-default @container overflow-hidden rounded-lg border"
				:aria-busy="loading || undefined"
			>
				<div
					class="bg-secondary border-default text-tertiary hidden items-center gap-4 border-b px-4 py-2 @3xl:grid"
					:class="COLUMNS"
				>
					<span :class="HEAD">Policy</span>
					<span :class="HEAD">Average score</span>
					<span :class="HEAD" class="text-right">Agents</span>
					<span :class="HEAD" class="text-right">Below {{ data?.weak_score ?? 50 }}%</span>
					<span :class="HEAD" class="text-right">Failed checks</span>
					<span />
				</div>

				<div v-if="!data" class="flex flex-col gap-3 p-3" data-testid="exposure-compliance-loading">
					<p class="text-secondary m-0 flex items-start gap-2 text-sm" role="status">
						<Icon name="carbon:renew" :size="16" class="text-primary mt-0.5 shrink-0 animate-spin" />
						<span>Asking Wazuh for every agent's policies. This can take a moment on a large fleet.</span>
					</p>
					<n-skeleton v-for="n of 4" :key="n" :height="48" :sharp="false" class="rounded-md" />
				</div>
				<n-empty
					v-else-if="!data.policies.length"
					:description="data.agents_in_scope ? 'No SCA results on your agents yet' : 'No agent to assess yet'"
					class="min-h-40 justify-center"
					data-testid="exposure-compliance-empty"
				/>
				<div v-else class="divide-border flex flex-col divide-y" :class="{ 'opacity-60': loading }">
					<!-- An open policy and its agents read as one group: one surface, one accent bar down its side. -->
					<div
						v-for="policy of data.policies"
						:key="policy.policy_id"
						class="transition-colors"
						:class="{
							'bg-secondary/40 shadow-[inset_3px_0_0_var(--primary-color)]': open === policy.policy_id
						}"
						data-testid="exposure-policy"
					>
						<button
							type="button"
							class="group hover:bg-secondary/50 focus-visible:outline-primary grid w-full cursor-pointer items-center gap-x-3 gap-y-1.5 px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 @3xl:gap-x-4 @3xl:gap-y-0"
							:class="COLUMNS_ROW"
							:aria-expanded="open === policy.policy_id"
							:data-policy="policy.policy_id"
							data-testid="exposure-policy-row"
							@click="toggle(policy.policy_id)"
						>
							<span class="flex min-w-0 flex-col gap-0.5 leading-tight [grid-area:name]">
								<span class="text-default truncate text-sm font-medium">
									<bdi>{{ policy.name || policy.policy_id }}</bdi>
								</span>
								<span class="text-tertiary truncate font-mono text-xs">{{ policy.policy_id }}</span>
							</span>
							<span class="flex min-w-0 items-center gap-2 [grid-area:score]">
								<span
									class="bg-secondary h-1.5 min-w-12 flex-1 overflow-hidden rounded-full"
									aria-hidden="true"
								>
									<span
										class="block h-full rounded-full"
										:class="SCORE_COLORS[scoreLevel(policy.average_score)]"
										:style="{ width: `${Math.max(1, policy.average_score)}%` }"
									/>
								</span>
								<span
									class="w-14 shrink-0 text-right font-mono text-sm font-semibold tabular-nums"
									data-testid="exposure-policy-score"
								>
									{{ policy.average_score }}%
								</span>
							</span>
							<span class="text-secondary text-right font-mono text-sm tabular-nums [grid-area:agents]">
								<span class="text-tertiary mr-1 text-xs uppercase @3xl:hidden">agents</span>
								{{ policy.agents.toLocaleString() }}
							</span>
							<span
								class="text-right font-mono text-sm tabular-nums [grid-area:below]"
								:class="policy.agents_below ? 'text-error' : 'text-tertiary'"
							>
								<span class="text-tertiary mr-1 text-xs uppercase @3xl:hidden">below</span>
								{{ policy.agents_below.toLocaleString() }}
							</span>
							<span
								class="text-secondary hidden text-right font-mono text-sm tabular-nums [grid-area:failed] @3xl:block"
							>
								{{ policy.failed.toLocaleString() }}
							</span>
							<Icon
								name="carbon:chevron-down"
								:size="14"
								class="text-tertiary group-hover:text-default justify-self-end transition-transform duration-200 [grid-area:chev]"
								:class="{ 'rotate-180': open === policy.policy_id }"
							/>
						</button>

						<div v-if="open === policy.policy_id" class="pb-2" data-testid="exposure-policy-agents">
							<p
								class="text-tertiary text-xxs m-0 px-4 pb-1.5 pl-9 font-medium tracking-[0.12em] uppercase"
							>
								Agents on this policy · {{ agentsLoading ? "…" : agents.length.toLocaleString() }},
								weakest first
							</p>
							<n-skeleton v-if="agentsLoading" text :repeat="3" class="px-4 pl-9" />
							<n-alert v-else-if="agentsError" type="error" :bordered="false" class="mx-4">
								{{ agentsError }}
							</n-alert>
							<ul v-else class="m-0 flex list-none flex-col p-0">
								<li v-for="agent of agents" :key="agent.agent_id" data-testid="exposure-policy-agent">
									<!-- The whole row opens the agent's SCA on this policy. -->
									<RouterLink
										:to="agentLink(agent.agent_id, { tab: 'sca', policy: policy.policy_id })"
										class="group/agent hover:bg-secondary/70 focus-visible:outline-primary grid items-center gap-x-3 gap-y-1 px-4 py-1.5 no-underline transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 @3xl:gap-x-4"
										:class="AGENT_ROW"
										data-testid="exposure-policy-agent-link"
									>
										<span class="flex min-w-0 items-center gap-2 [grid-area:name]">
											<!-- An elbow from the policy above: this row belongs to it. -->
											<span
												class="border-tertiary/50 ml-1.5 h-3 w-3 shrink-0 -translate-y-1 rounded-bl-sm border-b border-l"
												aria-hidden="true"
											/>
											<span
												class="text-default group-hover/agent:text-primary truncate text-sm transition-colors"
											>
												<bdi>{{ agent.hostname }}</bdi>
											</span>
										</span>
										<span class="flex min-w-0 items-center gap-2 [grid-area:score]">
											<span
												class="bg-secondary h-1 min-w-12 flex-1 overflow-hidden rounded-full"
												aria-hidden="true"
											>
												<span
													class="block h-full rounded-full"
													:class="SCORE_COLORS[scoreLevel(agent.score)]"
													:style="{ width: `${Math.max(1, agent.score)}%` }"
												/>
											</span>
											<span
												class="w-14 shrink-0 text-right font-mono text-sm font-semibold tabular-nums"
												:class="SCORE_TEXT[scoreLevel(agent.score)]"
											>
												{{ agent.score }}%
											</span>
										</span>
										<span
											class="text-secondary text-right font-mono text-xs tabular-nums [grid-area:failed] @3xl:text-sm"
										>
											{{ agent.failed.toLocaleString() }}
											<span class="@3xl:hidden">failed</span>
										</span>
									</RouterLink>
								</li>
							</ul>
						</div>
					</div>
				</div>

				<p
					v-if="data?.read_at"
					class="text-tertiary border-default border-t px-4 py-2 text-xs"
					data-testid="exposure-read-at"
				>
					Read from Wazuh at {{ formatDate(data.read_at, dFormats.datetime, { tz: true }) }}; refreshed every
					few minutes.
				</p>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { PolicyAgent } from "@/types/exposure"
import { NAlert, NButton, NEmpty, NSkeleton } from "naive-ui"
import { computed, ref } from "vue"
import { RouterLink } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { agentLink, SCORE_COLORS, scoreLevel } from "./exposure"
import ExposureDisabled from "./ExposureDisabled.vue"
import { useExposureCompliance } from "./useExposure"

/**
 * The Exposure page's compliance (#1289): SCA by policy across the customer's agents, the
 * weakest average first; a policy opens its agents, weakest first, each a link to that
 * agent's SCA on that policy. Agents Wazuh could not answer for are said, not hidden.
 */

const HEAD = "text-xxs font-medium tracking-[0.12em] uppercase"
const COLUMNS = "grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_4.5rem_6rem_6.5rem_1rem]"
const COLUMNS_ROW = [
	"grid-cols-[minmax(0,1fr)_auto_auto]",
	"[grid-template-areas:'name_name_chev'_'score_agents_below']",
	"@3xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_4.5rem_6rem_6.5rem_1rem]",
	"@3xl:[grid-template-areas:'name_score_agents_below_failed_chev']"
]
// An agent of an open policy lines up under the policy's own score and failed columns.
const AGENT_ROW = [
	"grid-cols-[minmax(0,1fr)_auto]",
	"[grid-template-areas:'name_failed'_'score_score']",
	"@3xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_4.5rem_6rem_6.5rem_1rem]",
	"@3xl:[grid-template-areas:'name_score_._._failed_.']"
]
const SCORE_TEXT = { good: "text-success", fair: "text-warning", poor: "text-error" } as const

const dFormats = useSettingsStore().dateFormat
const customerFilterStore = useCustomerFilterStore()
const { data, error, loading, reload } = useExposureCompliance()

const failure = computed(() => error.value || data.value?.error || null)
// No figures (—) while loading or when Wazuh could not be read: a 0 would read as "none".
const known = computed(() => !!data.value && !data.value.error)

function plural(count: number, word: string, many = `${word}s`) {
	return `${count.toLocaleString()} ${count === 1 ? word : many}`
}

const cards = computed(() => {
	const d = data.value
	const average = d?.average_score
	return [
		{
			key: "score",
			label: "Average score",
			value: average === null || average === undefined ? "—" : `${average}%`,
			caption: "across every agent and policy",
			tone: average === null || average === undefined ? "text-tertiary" : SCORE_TEXT[scoreLevel(average)]
		},
		{
			key: "agents",
			label: "Agents assessed",
			value: d ? `${d.agents_assessed.toLocaleString()} / ${d.agents_in_scope.toLocaleString()}` : "—",
			caption: "with at least one policy",
			tone: "text-default"
		},
		{
			key: "policies",
			label: "Policies",
			value: d ? d.policies.length.toLocaleString() : "—",
			caption: d
				? `${plural(d.policies.filter(p => p.agents_below).length, "policy", "policies")} with agents below ${d.weak_score}%`
				: "",
			tone: "text-default"
		},
		{
			key: "failed",
			label: "Failed checks",
			value: d ? d.failed.toLocaleString() : "—",
			caption: d ? `${d.passed.toLocaleString()} passed` : "",
			tone: d?.failed ? "text-error" : "text-default"
		}
	]
})

const open = ref<string | null>(null)
const agents = ref<PolicyAgent[]>([])
const agentsError = ref<string | null>(null)
const { loading: agentsLoading, run } = useLatestRequest()

function toggle(policyId: string) {
	if (open.value === policyId) {
		open.value = null
		return
	}
	open.value = policyId
	agents.value = []
	agentsError.value = null
	run(
		async signal => {
			const response = await Api.exposure.getPolicyAgents(
				policyId,
				customerFilterStore.queryCustomerCodes,
				signal
			)
			if (signal.aborted) return
			agents.value = response.data.agents
			agentsError.value = response.data.error
		},
		err => {
			agentsError.value = getApiErrorMessage(err as ApiError) || "Could not load the policy's agents."
		}
	)
}
</script>
