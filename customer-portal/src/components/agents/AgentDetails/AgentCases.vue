<template>
	<div class="flex flex-col gap-3" data-testid="agent-cases">
		<n-alert v-if="error" type="error" :bordered="false" data-testid="agent-cases-error">{{ error }}</n-alert>

		<section
			v-else
			class="border-default bg-default @container overflow-hidden rounded-lg border"
			:aria-busy="loading"
		>
			<header class="bg-secondary border-default flex items-baseline justify-between gap-2 border-b px-4 py-2">
				<span class="text-tertiary text-xs font-medium tracking-wider uppercase">
					Cases involving this host
				</span>
				<span v-if="!loading" class="text-tertiary font-mono text-xs tabular-nums">{{ cases.length }}</span>
			</header>

			<div v-if="loading" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 3" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!cases.length"
				description="No case involves this host"
				class="min-h-40 justify-center"
				data-testid="agent-cases-empty"
			/>
			<div v-else class="divide-border flex flex-col divide-y">
				<div
					v-for="c of cases"
					:key="c.id"
					class="hover:bg-secondary/50 grid items-center gap-x-3 gap-y-1.5 px-4 py-2.5 transition-colors @3xl:gap-x-4"
					:class="ROW"
					data-testid="agent-case-row"
				>
					<span class="[grid-area:status]">
						<Chip size="small" v-bind="statusTagProps(c.case_status)">
							{{ workflowStatusLabel(c.case_status).toUpperCase() }}
						</Chip>
					</span>
					<span class="flex min-w-0 flex-col leading-tight [grid-area:name]">
						<span class="text-default line-clamp-2 text-sm @3xl:line-clamp-1">{{ c.case_name }}</span>
						<span class="text-tertiary font-mono text-xs tabular-nums">
							#{{ c.id }} · {{ c.alerts?.length ?? 0 }} alert{{ c.alerts?.length === 1 ? "" : "s" }}
						</span>
					</span>
					<!-- Narrow: one line under the name; wide (contents): two columns of their own. -->
					<span
						class="text-secondary flex min-w-0 items-baseline gap-2 text-xs [grid-area:info] @3xl:contents"
					>
						<span class="truncate @3xl:[grid-area:owner]">{{ c.assigned_to ?? "unassigned" }}</span>
						<span class="text-tertiary @3xl:hidden">·</span>
						<span
							class="whitespace-nowrap @3xl:[grid-area:created]"
							:title="String(formatDate(c.case_creation_time, dFormats.datetime))"
						>
							{{ relative(c.case_creation_time) }}
						</span>
					</span>
					<span class="flex justify-end [grid-area:open]">
						<CaseDetailsButton :case-id="c.id" size="small" />
					</span>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { Case } from "@/types/cases"
import type { ApiError } from "@/types/common"
import { NAlert, NEmpty, NSkeleton } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CaseDetailsButton from "@/components/cases/CaseDetailsButton.vue"
import Chip from "@/components/common/Chip.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage, statusTagProps } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import { workflowStatusLabel } from "@/utils/workflowStatus"

/**
 * The cases with an alert on this host (#1256) — the agent's own customer's only: a host
 * name is no tenant key, and the backend narrows the cases to the agent's customer.
 */

const { hostname } = defineProps<{ hostname: string }>()

// Narrow, a small card: status and the case's buttons on top, then its name, then who and
// when; wide, one line under the header.
const ROW = [
	"grid-cols-[minmax(0,1fr)_auto]",
	"[grid-template-areas:'status_open'_'name_name'_'info_info']",
	"@3xl:grid-cols-[8rem_minmax(0,1fr)_9rem_7rem_auto]",
	"@3xl:[grid-template-areas:'status_name_owner_created_open']"
].join(" ")

const dFormats = useSettingsStore().dateFormat
const { loading, run } = useLatestRequest()
const cases = ref<Case[]>([])
const error = ref<string | null>(null)

const relative = (ts: Date | string) => dayjs(ts).fromNow()

onBeforeMount(() => {
	error.value = null
	run(
		async signal => {
			cases.value = (await Api.agents.getCases(hostname, signal)).data.cases ?? []
		},
		err => {
			error.value = getApiErrorMessage(err as ApiError) || "Could not load the cases."
		}
	)
})
</script>
