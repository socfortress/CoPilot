<template>
	<div
		v-if="!allowed"
		class="text-secondary flex flex-col gap-2 py-10 text-center text-sm"
		data-testid="talon-health-not-for-role"
	>
		<span>The Talon health dashboard isn't available for your role.</span>
		<a :href="TALON_DOCS.overview" target="_blank" rel="noopener noreferrer" class="text-primary">
			What Talon does
		</a>
	</div>
	<div v-else class="flex flex-col gap-4 pt-4" data-testid="talon-health">
		<!-- The banner: the verdict, version, uptime, how fresh, and a refresh. Only the verdict is a
		live region: "checked Ns ago" changes every second and must not be announced. -->
		<div
			class="border-default flex flex-wrap items-center justify-between gap-3 rounded-lg border border-l-4 px-4 py-3"
			:style="{ borderLeftColor: TONE_COLOR[bannerState.tone] }"
			data-testid="talon-health-banner"
			:data-tone="bannerState.tone"
		>
			<div class="flex min-w-0 items-center gap-3">
				<span class="flex shrink-0" :style="{ color: TONE_COLOR[bannerState.tone] }">
					<Icon :name="bannerState.icon" :size="24" />
				</span>
				<div class="flex min-w-0 flex-col" role="status" aria-live="polite" data-testid="talon-health-verdict">
					<span class="text-default text-lg font-semibold" data-testid="talon-health-banner-title">
						{{ bannerState.title }}
					</span>
					<span
						v-if="bannerState.reason"
						class="text-secondary text-sm break-words"
						data-testid="talon-health-banner-reason"
					>
						<bdi>{{ bannerState.reason }}</bdi>
					</span>
				</div>
			</div>
			<div class="text-secondary flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
				<span v-if="health?.version" data-testid="talon-health-version">
					talon-analyst
					<b class="text-default font-mono">
						<bdi>{{ health.version }}</bdi>
					</b>
				</span>
				<span v-if="uptime" data-testid="talon-health-uptime">
					up
					<b class="text-default">{{ uptime }}</b>
				</span>
				<span aria-live="off" data-testid="talon-health-checked">{{ checkedAgo }}</span>
				<n-button
					size="small"
					secondary
					:loading
					:disabled="loading"
					data-testid="talon-health-refresh"
					@click="load()"
				>
					<template #icon><Icon name="carbon:renew" :size="14" /></template>
					Refresh
				</n-button>
			</div>
		</div>

		<n-alert v-if="failure" type="error" :bordered="false" size="small" data-testid="talon-health-error">
			{{ failure }}
		</n-alert>

		<div v-if="!report && loading" class="flex justify-center py-16" data-testid="talon-health-loading">
			<n-spin size="medium" />
		</div>

		<div
			v-if="report"
			class="flex flex-col gap-4 transition-opacity"
			:class="{ 'opacity-60': loading }"
			data-testid="talon-health-body"
		>
			<SocPanel title="From CoPilot" caption="measured by CoPilot's backend">
				<TalonCopilotChecks :copilot="report.copilot" />
			</SocPanel>

			<n-alert
				v-if="report.health.unsupported"
				type="info"
				:bordered="false"
				title="Upgrade Talon for the health dashboard"
				data-testid="talon-health-old"
			>
				{{ OLD_TALON_TEXT }}.
				<a
					:href="`${TALON_DOCS.install}#upgrades`"
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary"
				>
					How to upgrade
				</a>
			</n-alert>

			<SocPanel title="Components">
				<div v-if="groups.length" class="flex flex-col gap-4" data-testid="talon-health-components">
					<div v-for="group of groups" :key="group.id" class="flex flex-col gap-2" :data-group="group.id">
						<span :class="SECTION_LABEL">{{ group.title }}</span>
						<div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
							<div
								v-for="component of group.components"
								:key="component.id"
								class="border-default flex flex-col gap-1.5 rounded-lg border p-3"
								data-testid="talon-health-component"
								:data-component="component.id"
							>
								<div class="flex items-center justify-between gap-2">
									<span class="truncate font-medium" :title="component.name">
										<bdi>{{ component.name }}</bdi>
									</span>
									<TalonHealthStatus :status="component.status" />
								</div>
								<div class="text-tertiary flex gap-3 text-xs">
									<span class="font-mono">{{ component.id }}</span>
									<span v-if="component.latency_ms !== null">
										{{ formatLatency(component.latency_ms) }}
									</span>
								</div>
								<p v-if="component.detail" class="text-secondary text-sm break-words">
									<bdi>{{ component.detail }}</bdi>
								</p>
								<n-collapse v-if="component.fix" class="mt-1">
									<n-collapse-item title="How to fix" :name="component.id">
										<p
											class="text-sm break-words whitespace-pre-line"
											data-testid="talon-health-fix"
										>
											<bdi>{{ component.fix }}</bdi>
										</p>
									</n-collapse-item>
								</n-collapse>
							</div>
						</div>
					</div>
				</div>
				<HealthUnavailable v-else :text="sectionProblem(report.health, 'Talon reported no components')" />
			</SocPanel>

			<!-- One window for everything below it: the uptime bars and the charts. -->
			<div class="flex flex-wrap items-center gap-3">
				<span class="text-secondary text-xs">History</span>
				<SegmentedToggle
					v-model="hours"
					:options="windowOptions"
					label="History window"
					test-id="talon-health-window"
				/>
			</div>

			<SocPanel title="Uptime" :caption="windowLabel">
				<TalonUptimeBars
					v-if="report.history.data"
					:components="health?.components ?? []"
					:history="report.history.data"
					:hours="report.hours"
				/>
				<HealthUnavailable v-else :text="sectionProblem(report.history)" />
			</SocPanel>

			<SocPanel title="Activity" :caption="windowLabel">
				<template v-if="report.metrics.data">
					<TalonHealthCharts
						v-if="report.metrics.data.series.length"
						:series="report.metrics.data.series"
						:hours="report.hours"
						:usage-available="usageAvailable && report.copilot.v2_enabled"
						@open-usage="emit('open-tab', 'usage')"
					/>
					<n-empty
						v-else
						description="No activity in this window"
						class="py-8"
						data-testid="talon-health-metrics-empty"
					/>
				</template>
				<HealthUnavailable v-else :text="sectionProblem(report.metrics)" />
			</SocPanel>

			<SocPanel title="Configuration" caption="as Talon reports it">
				<TalonHealthConfig v-if="health?.config" :config="health.config" :scope="report.copilot.scope" />
				<p v-else-if="health" class="text-tertiary py-4 text-sm" data-testid="talon-health-config-unavailable">
					Configuration unavailable: this Talon didn't report it.
				</p>
				<HealthUnavailable v-else :text="sectionProblem(report.health)" />
			</SocPanel>
		</div>

		<footer
			class="text-secondary flex flex-wrap items-center gap-x-4 gap-y-1 pb-4 text-xs"
			data-testid="talon-health-footer"
		>
			<a
				:href="TALON_DOCS.overview"
				target="_blank"
				rel="noopener noreferrer"
				class="text-primary inline-flex items-center gap-1 no-underline hover:underline"
				data-testid="talon-health-docs"
			>
				What Talon does and how to set it up
				<Icon name="carbon:launch" :size="11" />
			</a>
			<a
				:href="TALON_DOCS.health"
				target="_blank"
				rel="noopener noreferrer"
				class="text-primary inline-flex items-center gap-1 no-underline hover:underline"
			>
				About this dashboard
				<Icon name="carbon:launch" :size="11" />
			</a>
		</footer>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Overview tab: the Talon health dashboard (`GET /api/talon/health`), whatever
// the "Talon v2" setting says. Everyone who can open the page sees the same detail (failure reasons,
// URLs, configuration; never a secret); per-customer items come already scoped by the backend.
//
// States: loading (first load), an error from CoPilot itself (kept beside the last good render),
// Talon unreachable (the "From CoPilot" row says why, the other sections say "unavailable"), an
// older Talon without the health API (404: an upgrade notice, CoPilot's checks still shown), and
// empty sections. Refreshes every 60 s while this tab is shown and the browser tab is visible; a
// reload keeps the previous render, dimmed.
import type { TalonHealthReport, TalonSection } from "@/types/talonHealth"
import axios from "axios"
import { NAlert, NButton, NCollapse, NCollapseItem, NEmpty, NSpin } from "naive-ui"
import { getActivePinia } from "pinia"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import SocPanel from "@/components/socManagement/ui/SocPanel.vue"
import { TONE_COLOR } from "@/components/socManagement/utils"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import {
	banner,
	formatAgo,
	formatDuration,
	formatLatency,
	groupComponents,
	isHealthReport,
	OLD_TALON_TEXT,
	REFRESH_MS,
	secondsSince,
	TALON_DOCS,
	WINDOWS,
	WRONG_SHAPE_TEXT
} from "./health/health"
import HealthUnavailable from "./health/HealthUnavailable.vue"
import TalonCopilotChecks from "./health/TalonCopilotChecks.vue"
import TalonHealthCharts from "./health/TalonHealthCharts.vue"
import TalonHealthConfig from "./health/TalonHealthConfig.vue"
import TalonHealthStatus from "./health/TalonHealthStatus.vue"
import TalonUptimeBars from "./health/TalonUptimeBars.vue"

const { active = true, usageAvailable = false } = defineProps<{
	/** Whether the Overview tab is the one shown (the page keeps hidden tabs mounted). */
	active?: boolean
	/** Whether the page has a Usage tab (the "Talon v2" setting is on). */
	usageAvailable?: boolean
}>()
const emit = defineEmits<{ (e: "open-tab", tab: string): void }>()

// The API answers admins and analysts (a responder is one too); the page itself is open to every
// role, so anyone else gets a plain sentence instead of a request and an "HTTP 403".
const allowed = computed(() =>
	getActivePinia() ? useAuthStore().isRoleGranted([AuthUserRole.Admin, AuthUserRole.Analyst]) : false
)
const notForRole = ref(false)

const windowOptions = WINDOWS.map(w => ({ value: w.value as number, label: w.label }))

const report = ref<TalonHealthReport | null>(null)
const failure = ref<string | null>(null)
const loading = ref(false)
const hours = ref<number>(24)
const now = ref(Date.now())
let controller: AbortController | null = null
let lastLoad = 0

const health = computed(() => report.value?.health?.data ?? null)
const bannerState = computed(() => banner(report.value))
const groups = computed(() => groupComponents(health.value?.components))
const uptime = computed(() => formatDuration(health.value?.uptime_seconds))
const checkedAgo = computed(() => formatAgo(secondsSince(report.value?.checked_at, now.value)))
const windowLabel = computed(() => (hours.value > 24 ? "last 7 days" : "last 24 hours"))

function sectionProblem(section: TalonSection<unknown> | undefined, empty = "Talon sent nothing") {
	if (section?.unsupported) return OLD_TALON_TEXT
	return section?.error ?? empty
}

async function load() {
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	lastLoad = Date.now()
	try {
		const { data } = await Api.talonHealth.getHealth(hours.value, own.signal)
		if (controller !== own) return
		if (!isHealthReport(data)) {
			// A section missing would break the page: keep the last good render and say why.
			failure.value = WRONG_SHAPE_TEXT
			return
		}
		report.value = data
		failure.value = null
	} catch (err) {
		if (controller !== own || axios.isCancel(err)) return
		const status = axios.isAxiosError(err) ? err.response?.status : undefined
		if (status === 403) {
			notForRole.value = true
			failure.value = "The Talon health dashboard isn't available for your role."
			return
		}
		failure.value = status
			? `CoPilot could not load Talon's health (HTTP ${status})`
			: "CoPilot could not load Talon's health (no answer)"
	} finally {
		if (controller === own) loading.value = false
	}
}

function visible() {
	return active && document.visibilityState === "visible"
}

let timer: ReturnType<typeof setInterval> | null = null
let ticker: ReturnType<typeof setInterval> | null = null

/** The "checked Ns ago" clock runs only while it can be seen. */
function syncTicker() {
	if (visible() && !ticker) {
		now.value = Date.now()
		ticker = setInterval(() => (now.value = Date.now()), 1000)
	} else if (!visible() && ticker) {
		clearInterval(ticker)
		ticker = null
	}
}

function onVisibility() {
	syncTicker()
	if (visible() && !notForRole.value && Date.now() - lastLoad >= REFRESH_MS) load()
}

onMounted(() => {
	if (!allowed.value) return
	load()
	timer = setInterval(() => {
		if (visible() && !notForRole.value) load()
	}, REFRESH_MS)
	syncTicker()
	document.addEventListener("visibilitychange", onVisibility)
})

onBeforeUnmount(() => {
	controller?.abort()
	if (timer) clearInterval(timer)
	if (ticker) clearInterval(ticker)
	document.removeEventListener("visibilitychange", onVisibility)
})

watch(hours, () => load())
watch(
	() => active,
	() => onVisibility()
)
</script>
