<template>
	<div class="page flex flex-col pb-0!">
		<n-tabs v-model:value="activeTab" type="segment" animated tab-class="px-5!" class="[&_.n-tabs-nav]:mx-auto">
			<n-tab-pane name="overview" tab="Overview" display-directive="show:lazy">
				<!-- The Talon health dashboard, whatever the "Talon v2" setting says. -->
				<TalonOverview
					:active="activeTab === 'overview'"
					:usage-available="talonV2Available"
					@open-tab="activeTab = $event"
				/>
			</n-tab-pane>
			<n-tab-pane name="talon" tab="Talon Chat" display-directive="show:lazy">
				<!-- The v2 chat (threads, a customer per thread) only with the "Talon v2" setting on; else v1, unchanged. -->
				<template v-if="talonV2Settled">
					<TalonV2Chat v-if="talonV2Available" class="h-fixed" />
					<TalonChat v-else class="h-fixed" />
				</template>
				<div v-else class="h-fixed flex items-center justify-center">
					<n-spin size="small" />
				</div>
			</n-tab-pane>
			<!-- Talon's chat action proposals waiting in CoPilot: only with the "Talon v2" setting on. -->
			<n-tab-pane v-if="talonV2Available" name="approvals" display-directive="show:lazy">
				<template #tab>
					<span class="flex items-center gap-2" data-testid="talon-approvals-tab">
						Approvals
						<n-badge
							v-if="approvalsCount > 0"
							:value="approvalsCount"
							:max="99"
							type="warning"
							data-testid="talon-approvals-badge"
						/>
					</span>
				</template>
				<TalonApprovalsList class="pt-6" />
			</n-tab-pane>
			<!-- What Talon remembers (the memory API): only with the "Talon v2" setting on. -->
			<n-tab-pane v-if="talonV2Available" name="memory" tab="Memory" display-directive="show:lazy">
				<TalonMemory v-if="visited.has('memory')" class="pt-6" />
			</n-tab-pane>
			<!-- Talon's ops jobs and their findings (talon-analyst D96): only with the "Talon v2" setting on. -->
			<n-tab-pane v-if="talonV2Available" name="ops" tab="Ops" display-directive="show:lazy">
				<TalonOps v-if="visited.has('ops')" class="pt-6" :initial-finding="linkedFinding" />
			</n-tab-pane>
			<!-- Talon's cost (talon-analyst FR-COST-5): only with the "Talon v2" setting on. -->
			<n-tab-pane v-if="talonV2Available" name="usage" tab="Usage" display-directive="show:lazy">
				<TalonUsagePanel v-if="visited.has('usage')" class="pt-6" />
			</n-tab-pane>
			<!-- Budgets (FR-COST-4, decision B): an admin's only, with v2 on; the backend refuses anyone else. -->
			<n-tab-pane v-if="talonV2Available && isAdmin" name="budgets" tab="Budgets" display-directive="show:lazy">
				<TalonBudgets v-if="visited.has('budgets')" class="pt-6" />
			</n-tab-pane>
			<!-- The global automation switch (talon-analyst D85, AP-2): an admin's only, behind "Talon v2" (D54). -->
			<n-tab-pane v-if="talonV2Available && isAdmin" name="settings" tab="Settings" display-directive="show:lazy">
				<TalonAutomationSettings v-if="visited.has('settings')" class="pt-6" />
			</n-tab-pane>
			<n-tab-pane name="reports" tab="Reports" display-directive="show:lazy">
				<AlertsReportsList />
			</n-tab-pane>
			<n-tab-pane name="feedback" tab="Feedback" display-directive="show:lazy">
				<FeedbackDashboard class="pt-8" />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NBadge, NSpin, NTabPane, NTabs } from "naive-ui"
import { getActivePinia } from "pinia"
import { computed, defineAsyncComponent, inject, onBeforeUnmount, reactive, ref, watch } from "vue"
import { routeLocationKey } from "vue-router"
import AlertsReportsList from "@/components/aiAnalyst/AlertsReportsList.vue"
import FeedbackDashboard from "@/components/aiAnalyst/Feedback/FeedbackDashboard.vue"
import TalonOverview from "@/components/aiAnalyst/TalonOverview.vue"
import TalonChat from "@/components/talonChat/TalonChatContainer.vue"
import { useTalonApprovals, watchApprovals } from "@/composables/useTalonApprovals"
import { useTalonV2Availability } from "@/composables/useTalonV2Availability"
import { useAuthStore } from "@/stores/auth"

// Loaded only when the setting is on: with it off, the page is the v1 chat as before.
const TalonV2Chat = defineAsyncComponent(() => import("@/components/talonChat/v2/TalonV2Chat.vue"))
const TalonApprovalsList = defineAsyncComponent(() => import("@/components/talonChat/v2/TalonApprovalsList.vue"))
const TalonMemory = defineAsyncComponent(() => import("@/components/aiAnalyst/memory/TalonMemory.vue"))
const TalonOps = defineAsyncComponent(() => import("@/components/aiAnalyst/ops/TalonOps.vue"))
const TalonUsagePanel = defineAsyncComponent(() => import("@/components/aiAnalyst/usage/TalonUsagePanel.vue"))
const TalonBudgets = defineAsyncComponent(() => import("@/components/aiAnalyst/usage/TalonBudgets.vue"))
const TalonAutomationSettings = defineAsyncComponent(() => import("@/components/aiAnalyst/TalonAutomationSettings.vue"))

// `?tab=ops&finding=<id>` (an ops notification's link) opens the Ops tab on that finding. Read
// without `useRoute`, so the page also mounts without a router (its tests).
const route = inject(routeLocationKey, null)
const linkedTab = route?.query?.tab === "ops" ? "ops" : null
const linkedId = Number(route?.query?.finding)
const linkedFinding = linkedTab && Number.isSafeInteger(linkedId) && linkedId > 0 ? linkedId : null
const activeTab = ref(linkedTab ?? "overview")
const { available: talonV2Available, settled: talonV2Settled } = useTalonV2Availability()

// The cost tabs mount their content when first opened and keep it (the panes' `show:lazy`, held
// here too so nothing is asked for before the tab is).
const visited = reactive(new Set<string>())
watch(activeTab, tab => visited.add(tab), { immediate: true })
// A link to the Ops tab while "Talon v2" is off: there is no such tab, so the Overview instead.
watch(
	[talonV2Settled, talonV2Available],
	([settled, on]) => {
		if (settled && !on && activeTab.value === "ops") activeTab.value = "overview"
	},
	{ immediate: true }
)

// The Budgets tab is an admin's (decision B). Read only when v2 is on; with no store there is no
// session, so nobody is an admin.
const isAdmin = computed(() => (getActivePinia() ? useAuthStore().isAdmin : false))

// The Approvals badge: the pending list, read while this page is open and visible, only with v2 on.
const { count: approvalsCount } = useTalonApprovals()
let stopApprovals: (() => void) | null = null
watch(
	talonV2Available,
	on => {
		if (on && !stopApprovals) {
			stopApprovals = watchApprovals()
		} else if (!on && stopApprovals) {
			stopApprovals()
			stopApprovals = null
		}
	},
	{ immediate: true }
)
onBeforeUnmount(() => stopApprovals?.())
</script>

<style lang="scss">
.h-fixed {
	height: calc(100svh - var(--toolbar-height) - var(--view-padding) - 70px);
}
</style>
