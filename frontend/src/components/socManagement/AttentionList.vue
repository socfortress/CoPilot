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
						<button
							v-if="item.customer_code"
							type="button"
							class="peek-link inline-flex items-center gap-1 font-mono"
							:aria-label="`Open the overview of customer ${item.customer_code}`"
							:data-testid="`attention-customer-${item.entity}-${item.id}`"
							@click="open('customer', item.customer_code)"
						>
							<Icon name="carbon:enterprise" :size="12" />
							{{ item.customer_code }}
							<Icon name="carbon:launch" :size="11" class="peek-icon" />
						</button>
						<button
							v-if="item.assigned_to"
							type="button"
							class="peek-link inline-flex items-center gap-1"
							:aria-label="`Open the overview of user ${item.assigned_to}`"
							:data-testid="`attention-user-${item.entity}-${item.id}`"
							@click="open('user', item.assigned_to)"
						>
							<Icon name="carbon:user" :size="12" />
							{{ item.assigned_to }}
							<Icon name="carbon:launch" :size="11" class="peek-icon" />
						</button>
						<span v-else class="inline-flex items-center gap-1">
							<Icon name="carbon:user" :size="12" />
							unassigned
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
		<EntityOverviewModal :target="overview" @close="overview = null" />
	</div>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
// Open items a manager has to chase: breached first (most overdue on top), then the
// ones about to breach. Each row links to the alert or case itself, and its customer and
// assignee open their overview in a modal, without leaving the dashboard.
import type { OverviewTarget } from "./EntityOverviewModal.vue"
import type { AttentionItem } from "@/types/soc-management"
import { NEmpty } from "naive-ui"
import { shallowRef } from "vue"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import EntityOverviewModal from "./EntityOverviewModal.vue"
import SeverityTag from "./ui/SeverityTag.vue"
import SlaStateTag from "./ui/SlaStateTag.vue"
import { clockLabel, formatOverdue, TONE_COLOR } from "./utils"

const { items } = defineProps<{ items: AttentionItem[] }>()

const overview = shallowRef<OverviewTarget | null>(null)

function open(kind: OverviewTarget["kind"], key: string) {
	overview.value = { kind, key }
}

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

.peek-link {
	border-radius: 4px;
	color: inherit;
	cursor: pointer;
	transition: color 0.15s var(--bezier-ease, ease);
}

.peek-link:hover,
.peek-link:focus-visible {
	color: var(--primary-color);
}

.peek-link:focus-visible {
	outline: 1px solid var(--primary-color);
	outline-offset: 2px;
}

.peek-icon {
	opacity: 0;
	transition: opacity 0.15s var(--bezier-ease, ease);
}

.peek-link:hover .peek-icon,
.peek-link:focus-visible .peek-icon {
	opacity: 1;
}

@media (hover: none) {
	.peek-icon {
		opacity: 1;
	}
}
</style>
