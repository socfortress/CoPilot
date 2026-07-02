<template>
	<div>
		<div v-if="collapsed" class="flex flex-col items-center gap-2">
			<n-tooltip placement="right">
				<template #trigger>
					<div class="flex items-center justify-center">
						<Icon
							:name="context?.is_outdated ? UpdateIcon : VersionIcon"
							:size="18"
							:class="context?.is_outdated ? 'text-warning' : 'text-secondary'"
						/>
					</div>
				</template>
				<div class="max-w-56 text-xs">
					<div class="font-mono">v{{ context?.current_version ?? "—" }}</div>
					<div v-if="context?.environment" class="text-secondary mt-0.5 uppercase">
						{{ context.environment }}
					</div>
					<div v-if="context?.is_outdated" class="text-warning mt-1">
						Update available: v{{ context?.latest_version }}
					</div>
				</div>
			</n-tooltip>

			<n-tooltip placement="right">
				<template #trigger>
					<button
						type="button"
						class="hover:bg-secondary/10 flex items-center justify-center rounded-md p-1 transition-colors"
						@click="refresh"
					>
						<Icon :name="healthIcon" :size="18" :class="healthIconClass" />
					</button>
				</template>
				<div class="max-w-72 text-xs">
					<div class="text-secondary mb-1 font-medium uppercase">{{ healthSummary }}</div>
					<n-scrollbar v-if="issueIndicators.length" class="max-h-48" trigger="none">
						<ul class="flex flex-col gap-1">
							<li v-for="indicator in issueIndicators.slice(0, 12)" :key="indicator.id">
								<span class="font-medium">{{ indicator.label }}:</span>
								{{ indicator.detail }}
							</li>
						</ul>
					</n-scrollbar>
					<div v-else class="text-secondary">All monitored services are healthy.</div>
				</div>
			</n-tooltip>
		</div>

		<div v-else class="flex flex-col gap-4">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-4 px-px">
					<div class="text-secondary text-2xs uppercase">Deployment</div>
					<n-tooltip v-if="context?.is_outdated && context?.release_url" placement="top" class="text-xs!">
						<template #trigger>
							<a
								:href="context.release_url"
								target="_blank"
								rel="noopener noreferrer"
								class="text-warning hover:text-warning/80 text-2xs inline-flex items-center gap-1 font-medium"
							>
								<Icon :name="UpdateIcon" :size="12" />
								Update
							</a>
						</template>
						v{{ context.latest_version }} available
					</n-tooltip>
				</div>

				<div class="flex items-center gap-2 px-px">
					<span class="font-mono text-xs">v{{ context?.current_version ?? "—" }}</span>
					<n-tag v-if="context?.environment" size="tiny" :bordered="false" class="text-3xs! uppercase">
						{{ context.environment }}
					</n-tag>
					<n-spin v-if="loading" :size="12" />
				</div>
			</div>

			<div v-if="indicators?.length" class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2 px-px">
					<div class="text-secondary text-2xs uppercase">Health</div>
					<button
						v-if="indicators.length"
						type="button"
						class="text-secondary hover:text-primary text-2xs"
						@click="showAllIndicators = !showAllIndicators"
					>
						{{ showAllIndicators ? "Compact view" : `Show all (${indicators.length})` }}
					</button>
				</div>

				<div v-if="loadError" class="text-error text-2xs px-px">
					{{ loadError }}
				</div>

				<n-scrollbar v-else class="max-h-36 rounded-lg" trigger="none">
					<div
						v-if="allHealthy && !showAllIndicators"
						class="text-secondary flex items-center gap-2 px-1 py-1 text-xs"
					>
						<Icon :name="OkIcon" :size="14" class="text-success shrink-0" />
						All monitored systems are healthy.
					</div>

					<div v-else class="flex flex-col gap-2">
						<n-card
							v-for="group in groupedIndicators"
							:key="group.key"
							content-class="flex flex-col gap-2 px-2! py-1.5!"
						>
							<div class="text-2xs">{{ group.label }}</div>

							<div class="flex flex-col gap-3">
								<div v-for="indicator in group.items" :key="indicator.id">
									<div class="flex items-start gap-2">
										<Icon
											:name="statusIcon(indicator.status)"
											:size="14"
											:class="statusClass(indicator.status)"
											class="mt-px"
										/>
										<div class="min-w-0 flex-1">
											<div class="flex items-center gap-1 text-xs leading-tight">
												<component
													:is="indicatorLink(indicator.id) ? 'router-link' : 'div'"
													:to="indicatorLink(indicator.id)"
													:class="{ 'cursor-pointer': indicatorLink(indicator.id) }"
												>
													<span>{{ indicator.label }}</span>
												</component>
												<span
													v-if="indicator.count && indicator.count > 0"
													class="bg-secondary text-secondary text-2xs rounded px-1 font-mono"
												>
													{{ indicator.count }}
												</span>
											</div>
											<p
												v-if="
													indicator.detail && (indicator.status !== 'ok' || showAllIndicators)
												"
												class="text-secondary text-2xs mt-0.5 line-clamp-2 leading-snug"
											>
												{{ indicator.detail }}
											</p>
										</div>
									</div>
								</div>
							</div>
						</n-card>
					</div>
				</n-scrollbar>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { RouteLocationRaw } from "vue-router"
import type { SidebarHealthIndicator, SidebarIndicatorStatus } from "@/types/sidebar-context"
import { NCard, NScrollbar, NSpin, NTag, NTooltip } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSidebarContext } from "@/composables/useSidebarContext"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()

const VersionIcon = "carbon:information"
const UpdateIcon = "carbon:update-now"
const OkIcon = "carbon:checkmark-filled"
const WarningIcon = "carbon:warning-filled"
const ErrorIcon = "carbon:error-filled"

const showAllIndicators = ref(false)

const categoryLabels: Record<string, string> = {
	triage: "Triage",
	ai: "AI & automation",
	operations: "Operations",
	infrastructure: "Infrastructure",
	platform: "Platform"
}

const categoryOrder = ["triage", "ai", "operations", "infrastructure", "platform"]

const { context, loading, loadError, indicators, issueIndicators, overallStatus, refresh } = useSidebarContext()

const visibleIndicators = computed(() => {
	if (showAllIndicators.value) {
		return indicators.value
	}
	if (issueIndicators.value.length === 0) {
		return []
	}
	return issueIndicators.value
})

const allHealthy = computed(() => issueIndicators.value.length === 0 && indicators.value.length > 0)

const groupedIndicators = computed(() => {
	const groups = new Map<string, SidebarHealthIndicator[]>()

	for (const indicator of visibleIndicators.value) {
		const key = indicator.category || "other"
		const current = groups.get(key) ?? []
		current.push(indicator)
		groups.set(key, current)
	}

	const orderedKeys = [
		...categoryOrder.filter(key => groups.has(key)),
		...Array.from(groups.keys()).filter(key => !categoryOrder.includes(key))
	]

	return orderedKeys.map(key => ({
		key,
		label: categoryLabels[key] ?? key,
		items: groups.get(key) ?? []
	}))
})

const healthIcon = computed(() => {
	if (overallStatus.value === "error") {
		return ErrorIcon
	}
	if (overallStatus.value === "warning") {
		return WarningIcon
	}
	return OkIcon
})

const healthIconClass = computed(() => statusClass(overallStatus.value))

const healthSummary = computed(() => {
	if (loadError.value) {
		return "Health check unavailable"
	}
	if (issueIndicators.value.length === 0) {
		return "All systems healthy"
	}
	const count = issueIndicators.value.length
	return `${count} issue${count === 1 ? "" : "s"} detected`
})

function statusIcon(status: SidebarIndicatorStatus) {
	if (status === "error") {
		return ErrorIcon
	}
	if (status === "warning") {
		return WarningIcon
	}
	return OkIcon
}

function statusClass(status: SidebarIndicatorStatus) {
	if (status === "error") {
		return "text-error shrink-0"
	}
	if (status === "warning") {
		return "text-warning shrink-0"
	}
	return "text-success shrink-0"
}

function indicatorLink(id: string): RouteLocationRaw | undefined {
	const routes: Record<string, RouteLocationRaw> = {
		open_alerts: { name: "IncidentManagement-Alerts" },
		my_open_cases: { name: "IncidentManagement-Cases" },
		tag_rbac: { name: "Users" },
		ai_analyst_jobs: { name: "AiAnalyst" },
		mem_palace: { name: "AiAnalyst" },
		notification_dispatch: { name: "Customers" },
		connectors: { name: "Connectors" },
		talon: { name: "Connectors" },
		core_soc_tools: { name: "Connectors" },
		wazuh_indexer: { name: "Indices" },
		wazuh_catalog: { name: "DetectionCatalog" },
		influx_health: { name: "Healthcheck" },
		scheduler: { name: "Scheduler" },
		agent_sync: { name: "Scheduler" },
		license: { name: "License" },
		platform_storage: { name: "Connectors" }
	}

	return routes[id]
}
</script>
