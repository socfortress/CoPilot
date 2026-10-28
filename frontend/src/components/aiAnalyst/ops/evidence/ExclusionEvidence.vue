<template>
	<div v-if="view" class="flex flex-col gap-3" data-testid="talon-ops-evidence-exclusion">
		<n-alert
			v-if="view.managerWide"
			type="warning"
			:bordered="false"
			title="Applies manager-wide"
			data-testid="talon-ops-evidence-manager-wide"
		>
			A Wazuh rule built from this candidate applies to every agent on the Wazuh manager, for every customer
			it serves<template v-if="view.asset">, not only to <bdi>{{ view.asset }}</bdi></template>.
		</n-alert>
		<div class="grid grid-cols-3 gap-2" role="list" aria-label="Verdicts">
			<div
				v-for="item of view.verdicts"
				:key="item.key"
				class="border-default flex flex-col rounded-md border px-2 py-1"
				role="listitem"
				:data-testid="`talon-ops-evidence-verdict-${item.key}`"
			>
				<span class="text-secondary text-xs">{{ item.label }}</span>
				<span class="font-mono text-base tabular-nums">{{ item.text }}</span>
			</div>
		</div>
		<ul v-if="view.guards.length" class="flex flex-col gap-0.5 text-sm" aria-label="Guards">
			<li
				v-for="guard of view.guards"
				:key="guard.key"
				class="inline-flex items-center gap-1.5"
				:data-passed="guard.passed === null ? 'unknown' : String(guard.passed)"
				:data-testid="`talon-ops-evidence-guard-${guard.key}`"
			>
				<Icon
					:name="guard.passed ? 'carbon:checkmark-filled' : guard.passed === false ? 'carbon:warning-alt-filled' : 'carbon:help'"
					:size="14"
					:class="guard.passed ? 'text-success' : guard.passed === false ? 'text-warning' : 'text-tertiary'"
				/>
				<span>{{ guard.label }}</span>
				<span v-if="guard.passed === false" class="text-warning">: {{ guard.count?.toLocaleString() }} found</span>
				<span v-else-if="guard.passed === null" class="text-tertiary">: not recorded</span>
				<span class="sr-only">{{ guard.passed ? "passed" : guard.passed === false ? "failed" : "" }}</span>
			</li>
		</ul>
		<EvidenceFigures :items="view.figures" />
	</div>
</template>

<script setup lang="ts">
// `exclusion_candidates`: the verdict counts, the rule-wide guards as a checklist, and, when
// `host_scoped` is false, that the rule applies manager-wide. The artifact stays in its own block.
import type { Evidence } from "./evidence"
import { NAlert } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { exclusionView } from "./evidence"
import EvidenceFigures from "./EvidenceFigures.vue"

const { evidence } = defineProps<{ evidence: Evidence | null }>()
const view = computed(() => exclusionView(evidence))
</script>
