<template>
	<div class="flex flex-col" data-testid="sla-targets">
		<table v-for="group of groups" :key="group.entity" class="w-full text-sm" :data-testid="`sla-targets-${group.entity}`">
			<caption class="text-tertiary px-5 pt-4 pb-1 text-left font-mono text-[11px] tracking-wider uppercase">
				{{ group.title }}
			</caption>
			<thead>
				<tr class="text-tertiary text-left text-xs">
					<th scope="col" class="px-5 py-2 font-medium">Severity</th>
					<th scope="col" class="px-2 py-2 font-medium">Response</th>
					<th scope="col" class="px-2 py-2 font-medium">Resolution</th>
					<th scope="col" class="px-5 py-2 text-right font-medium">Kept</th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="row of group.rows"
					:key="row.severity"
					class="border-default border-t"
					:data-testid="`sla-target-${group.entity}-${row.severity.toLowerCase()}`"
				>
					<th scope="row" class="px-5 py-2.5 text-left font-medium">
						<span class="flex items-center gap-2">
							<span class="size-2 shrink-0 rounded-full" :class="bgClass(severityColor(row.severity))" />
							{{ row.severity }}
						</span>
					</th>
					<td class="px-2 py-2.5 font-mono text-xs tabular-nums">{{ formatTarget(row.acknowledge_minutes) }}</td>
					<td class="px-2 py-2.5 font-mono text-xs tabular-nums">
						<span class="flex flex-wrap items-center gap-1.5">
							{{ formatTarget(row.resolve_minutes) }}
							<n-tooltip v-if="row.business_hours">
								<template #trigger>
									<span
										class="border-default text-tertiary rounded border px-1 font-sans text-[10px] leading-4"
										data-testid="sla-business-hours"
									>
										business hours
									</span>
								</template>
								These targets count working hours only: nights, weekends and holidays do not run the clock.
							</n-tooltip>
						</span>
					</td>
					<td class="px-5 py-2.5 text-right font-mono text-xs tabular-nums">
						<span v-if="row.opened" :class="keptClass(row.resolve_rate ?? row.acknowledge_rate)">
							{{ formatRate(row.resolve_rate ?? row.acknowledge_rate) }}
						</span>
						<span v-else class="text-tertiary" title="Nothing of this severity in the period">—</span>
					</td>
				</tr>
			</tbody>
		</table>
		<p class="text-tertiary px-5 pt-3 pb-4 text-xs">
			Kept: the share resolved within target (or answered, when resolution has no outcome yet). Time spent
			waiting on you does not count against the SOC.
		</p>
	</div>
</template>

<script setup lang="ts">
import type { TargetGroup } from "./sla"
import { NTooltip } from "naive-ui"
import { bgClass, severityColor, textClass } from "@/components/overview/shared/status"
import { formatRate, formatTarget, rateTone } from "./sla"

defineProps<{
	groups: TargetGroup[]
}>()

function keptClass(rate: number | null) {
	const tone = rateTone(rate)
	return tone === "neutral" ? "text-tertiary" : textClass(tone)
}
</script>
