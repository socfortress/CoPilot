<template>
	<div class="attention-list flex flex-col" data-testid="attention-list">
		<n-empty v-if="!items.length" description="Nothing open is past or close to its SLA" class="py-8">
			<template #icon>
				<Icon name="carbon:checkmark-outline" />
			</template>
		</n-empty>
		<ul v-else class="divide-border m-0 flex list-none flex-col divide-y p-0">
			<li
				v-for="item of items"
				:key="`${item.entity}-${item.id}`"
				class="attention-row hover:bg-secondary group grid items-center gap-x-3 gap-y-1 px-3 py-2 transition-colors"
				:data-state="item.state"
			>
				<span class="state-rail h-8 w-0.5 rounded-full" :style="{ backgroundColor: railColor(item) }" />
				<div class="flex min-w-0 flex-col gap-0.5">
					<div class="flex min-w-0 items-center gap-2">
						<RouterLink
							:to="link(item)"
							class="text-primary shrink-0 font-mono text-xs font-medium hover:underline"
							:data-testid="`attention-link-${item.entity}-${item.id}`"
						>
							{{ item.entity === "alert" ? "ALERT" : "CASE" }}-{{ item.id }}
						</RouterLink>
						<span class="text-default line-clamp-1 text-sm" :title="item.title">{{ item.title }}</span>
					</div>
					<div class="text-tertiary flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs">
						<SeverityTag :severity="item.severity" />
						<span v-if="item.customer_code" class="font-mono">{{ item.customer_code }}</span>
						<span class="inline-flex items-center gap-1">
							<Icon name="carbon:user" :size="12" />
							{{ item.assigned_to ?? "unassigned" }}
						</span>
					</div>
				</div>
				<div class="flex flex-col items-end gap-0.5 text-right">
					<SlaStateTag
						:state="item.state"
						:label="`${clockLabel(item.clock)} ${item.state === 'breached' ? 'breached' : 'at risk'}`"
					/>
					<span class="font-mono text-xs tabular-nums" :style="{ color: railColor(item) }">
						{{ formatOverdue(item.overdue_seconds) }}
					</span>
				</div>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
// Open items a manager has to chase: breached first (most overdue on top), then the
// ones about to breach. Each row links to the alert or case itself.
import type { RouteLocationRaw } from "vue-router"
import type { AttentionItem } from "@/types/soc-management"
import { NEmpty } from "naive-ui"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import SeverityTag from "./ui/SeverityTag.vue"
import SlaStateTag from "./ui/SlaStateTag.vue"
import { clockLabel, formatOverdue, TONE_COLOR } from "./utils"

const { items } = defineProps<{ items: AttentionItem[] }>()

function link(item: AttentionItem): RouteLocationRaw {
	return item.entity === "alert"
		? { name: "IncidentManagement-Alert", params: { id: String(item.id) } }
		: { name: "IncidentManagement-Case", params: { id: String(item.id) } }
}

function railColor(item: AttentionItem) {
	return item.state === "breached" ? TONE_COLOR.bad : TONE_COLOR.warn
}
</script>

<style scoped>
.attention-row {
	grid-template-columns: auto minmax(0, 1fr) auto;
}
</style>
