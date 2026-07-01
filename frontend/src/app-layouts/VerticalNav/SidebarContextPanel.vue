<template>
	<div class="flex flex-col gap-2 border-t border-default pt-2">
		<div v-if="collapsed" class="flex flex-col items-center gap-2 py-1">
			<n-tooltip placement="right">
				<template #trigger>
					<div class="flex items-center justify-center">
						<Icon :name="VersionIcon" :size="18" class="text-secondary" />
						<span
							v-if="context?.is_outdated"
							class="bg-warning ml-0.5 inline-block size-1.5 rounded-full"
						/>
					</div>
				</template>
				<div class="max-w-56 text-xs">
					<div class="font-mono">v{{ context?.current_version ?? "—" }}</div>
					<div v-if="context?.is_outdated" class="text-warning mt-1">
						Update available: v{{ context?.latest_version }}
					</div>
				</div>
			</n-tooltip>

			<n-tooltip placement="right">
				<template #trigger>
					<button
						type="button"
						class="flex items-center justify-center rounded-md p-1 transition-colors hover:bg-secondary/10"
						@click="refresh"
					>
						<Icon :name="healthIcon" :size="18" :class="healthIconClass" />
					</button>
				</template>
				<div class="max-w-64 text-xs">
					<div class="mb-1 font-medium">{{ healthSummary }}</div>
					<ul v-if="issueIndicators.length" class="flex flex-col gap-1">
						<li v-for="indicator in issueIndicators" :key="indicator.id">
							<span class="font-medium">{{ indicator.label }}:</span>
							{{ indicator.detail }}
						</li>
					</ul>
					<div v-else class="text-secondary">All monitored services are healthy.</div>
				</div>
			</n-tooltip>
		</div>

		<template v-else>
			<div class="flex items-center justify-between gap-2 px-px">
				<div class="text-secondary text-2xs uppercase">Deployment</div>
				<n-tooltip v-if="context?.is_outdated && context.release_url" placement="top">
					<template #trigger>
						<a
							:href="context.release_url"
							target="_blank"
							rel="noopener noreferrer"
							class="text-warning hover:text-warning/80 inline-flex items-center gap-1 text-2xs font-medium"
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
				<n-spin v-if="loading" :size="12" />
			</div>

			<div class="text-secondary text-2xs px-px uppercase">Health</div>

			<div v-if="loadError" class="text-error text-2xs px-px">
				{{ loadError }}
			</div>

			<ul v-else class="flex flex-col gap-1">
				<li v-for="indicator in indicators" :key="indicator.id">
					<component
						:is="indicatorLink(indicator.id) ? 'router-link' : 'div'"
						:to="indicatorLink(indicator.id)"
						class="hover:bg-secondary/10 flex items-start gap-2 rounded-md px-1 py-1 transition-colors"
						:class="{ 'cursor-pointer': indicatorLink(indicator.id) }"
					>
						<Icon :name="statusIcon(indicator.status)" :size="14" :class="statusClass(indicator.status)" />
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-1 text-xs leading-tight">
								<span>{{ indicator.label }}</span>
								<span
									v-if="indicator.count && indicator.count > 0"
									class="bg-default text-secondary rounded px-1 text-2xs font-mono"
								>
									{{ indicator.count }}
								</span>
							</div>
							<p
								v-if="indicator.detail && indicator.status !== 'ok'"
								class="text-secondary mt-0.5 line-clamp-2 text-2xs leading-snug"
							>
								{{ indicator.detail }}
							</p>
						</div>
					</component>
				</li>
			</ul>
		</template>
	</div>
</template>

<script lang="ts" setup>
import type { SidebarIndicatorStatus } from "@/types/sidebar-context"
import type { RouteLocationRaw } from "vue-router"
import { NSpin, NTooltip } from "naive-ui"
import { computed } from "vue"
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

const { context, loading, loadError, indicators, issueIndicators, overallStatus, refresh } = useSidebarContext()

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
	if (id === "connectors") {
		return { name: "Connectors" }
	}
	if (id === "scheduler") {
		return { name: "Scheduler" }
	}
	if (id === "wazuh_catalog") {
		return { name: "DetectionCatalog" }
	}
	return undefined
}
</script>
