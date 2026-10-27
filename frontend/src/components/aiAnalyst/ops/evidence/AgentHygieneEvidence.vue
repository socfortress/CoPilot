<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-agent-hygiene">
		<EvidenceFigures :items="view.figures" />
		<div class="overflow-x-auto">
			<table class="w-full text-left text-xs" data-testid="talon-ops-evidence-agents">
				<thead class="text-secondary">
					<tr>
						<th class="py-1 pr-3 font-medium">Agent</th>
						<th class="py-1 pr-3 font-medium">Hostname</th>
						<th v-if="view.hasVersion" class="py-1 pr-3 font-medium">Version</th>
						<th class="py-1 font-medium">Critical asset</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row of view.rows"
						:key="row.id"
						class="border-default border-t"
						data-testid="talon-ops-evidence-agent"
					>
						<td class="py-1 pr-3 font-mono">
							<router-link
								v-if="row.to"
								:to="row.to"
								class="text-primary no-underline hover:underline"
								:data-testid="`talon-ops-evidence-agent-link-${row.id}`"
							>
								<bdi>{{ row.id }}</bdi>
							</router-link>
							<bdi v-else>{{ row.id }}</bdi>
						</td>
						<td class="py-1 pr-3"><bdi>{{ row.hostname ?? "—" }}</bdi></td>
						<td v-if="view.hasVersion" class="py-1 pr-3 font-mono"><bdi>{{ row.version ?? "—" }}</bdi></td>
						<td class="py-1">
							<span v-if="row.critical" class="text-warning inline-flex items-center gap-1">
								<Icon name="carbon:warning-alt-filled" :size="12" />
								yes
							</span>
							<span v-else>{{ yesNo(row.critical) }}</span>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p v-if="view.more" class="text-tertiary text-xs" data-testid="talon-ops-evidence-agents-more">
			+{{ view.more.toLocaleString() }} more
		</p>
	</div>
</template>

<script setup lang="ts">
// `agent_hygiene`: the group's agents (id, hostname, version, critical asset), each id linked to its
// agent page when it is a plain id (`LINK_ID`, as `findingLinks`), and "+N more" past Talon's 25.
import type { Evidence } from "./evidence"
import { computed } from "vue"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { agentHygieneView, yesNo } from "./evidence"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence, kind } = defineProps<{ evidence: Evidence | null; kind: string }>()
const view = computed(() => agentHygieneView(evidence, kind))
</script>
