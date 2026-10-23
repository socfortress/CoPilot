<template>
	<div v-if="!allowed" class="text-secondary py-10 text-center text-sm" data-testid="talon-memory-not-for-role">
		Talon's memory isn't available for your role.
	</div>
	<div v-else class="flex flex-col gap-4" data-testid="talon-memory">
		<n-tabs v-model:value="section" type="line" size="small" animated>
			<n-tab-pane name="customer" tab="Customer memory" display-directive="show:lazy">
				<div class="flex flex-col gap-4 pt-2">
					<div class="flex flex-wrap items-end justify-between gap-3">
						<label class="flex flex-col gap-1">
							<span class="text-secondary text-xs">Customer</span>
							<n-select
								v-model:value="customer"
								:options="customerOptions"
								:loading="customersLoading"
								placeholder="Choose a customer"
								filterable
								size="small"
								class="w-72!"
								data-testid="talon-memory-customer"
							/>
						</label>
						<div class="flex items-center gap-3">
							<a
								:href="MEMORY_DOCS"
								target="_blank"
								rel="noopener noreferrer"
								class="text-primary inline-flex items-center gap-1 text-xs no-underline hover:underline"
							>
								What Talon remembers
								<Icon name="carbon:launch" :size="11" />
							</a>
							<n-button
								v-if="customer"
								size="small"
								secondary
								:loading="statsLoading"
								:disabled="statsLoading"
								data-testid="talon-memory-refresh"
								@click="refresh()"
							>
								<template #icon><Icon name="carbon:renew" :size="14" /></template>
								Refresh
							</n-button>
						</div>
					</div>

					<p
						v-if="!customer"
						class="text-tertiary py-10 text-center text-sm"
						data-testid="talon-memory-choose"
					>
						{{
							customersLoading || customerOptions.length
								? "Choose a customer to see what Talon remembers about them."
								: "You have no customers assigned, so there is no memory to show."
						}}
					</p>
					<template v-else>
						<MemoryOverview
							:stats
							:loading="statsLoading"
							:problem="statsProblem"
							@retry="loadStats()"
							@filter="applyFilter"
						/>
						<template v-if="!blocked">
							<n-radio-group v-model:value="view" size="small" name="talon-memory-view" aria-label="Show">
								<n-radio-button value="drawers" data-testid="talon-memory-view-drawers">
									Memories
								</n-radio-button>
								<n-radio-button value="assets" data-testid="talon-memory-view-assets">
									Assets
								</n-radio-button>
							</n-radio-group>
							<MemoryDrawers
								v-if="view === 'drawers'"
								ref="drawersList"
								v-model:room="room"
								v-model:source="source"
								:customer-code="customer"
								@open="openDrawer = $event.drawer_id"
							/>
							<MemoryAssets v-else :customer-code="customer" />
						</template>
					</template>
				</div>
			</n-tab-pane>
			<n-tab-pane name="chat" tab="My chat memory" display-directive="show:lazy">
				<MemoryChat class="pt-2" />
			</n-tab-pane>
		</n-tabs>

		<MemoryDrawerDetail
			v-if="customer"
			:customer-code="customer"
			:drawer-id="openDrawer"
			@close="openDrawer = null"
			@forgotten="onForgotten"
		/>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Memory tab (only with the "Talon v2" setting on): what Talon remembers about
// one of the caller's customers (stats, growth, the room and source breakdowns, the memories with
// filters and a search, the assets' timelines) and the caller's own chat memory. Every request goes
// through CoPilot, which checks the customer is the caller's; CoPilot's own "Not Found" means the
// setting was turned off meanwhile, talon-analyst's means a Talon without the memory API (both shown
// in words, never as a status code).
//
// States: no customer chosen, loading (first load), the stats' problem (v2 off, an old Talon, a
// failure with a retry) which also hides the list, empty sections, and the detail drawer's own.
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonMemoryRoom, TalonMemorySource, TalonMemoryStats } from "@/types/talonMemory"
import { NButton, NRadioButton, NRadioGroup, NSelect, NTabPane, NTabs } from "naive-ui"
import { getActivePinia } from "pinia"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import Icon from "@/components/common/Icon.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { MEMORY_DOCS, problemState } from "./memory"
import MemoryAssets from "./MemoryAssets.vue"
import MemoryChat from "./MemoryChat.vue"
import MemoryDrawerDetail from "./MemoryDrawerDetail.vue"
import MemoryDrawers from "./MemoryDrawers.vue"
import MemoryOverview from "./MemoryOverview.vue"

// The routes answer admins and analysts (a responder is one too).
const allowed = computed(() =>
	getActivePinia() ? useAuthStore().isRoleGranted([AuthUserRole.Admin, AuthUserRole.Analyst]) : false
)

const { globalCustomerCode, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()
const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()

const section = ref<"customer" | "chat">("customer")
const view = ref<"drawers" | "assets">("drawers")
const customer = ref<string | null>(null)
const room = ref<TalonMemoryRoom | null>(null)
const source = ref<TalonMemorySource | null>(null)
const openDrawer = ref<string | null>(null)
const drawersList = ref<InstanceType<typeof MemoryDrawers> | null>(null)

const stats = ref<TalonMemoryStats | null>(null)
const statsFailure = ref<TalonMemoryFailure | null>(null)
const statsLoading = ref(false)
let controller: AbortController | null = null

const statsProblem = computed(() => problemState(statsFailure.value))
// v2 off or an old Talon: the list can't answer either, so only the notice shows.
const blocked = computed(() => statsProblem.value !== null && statsProblem.value.kind !== "error")
const codes = computed(() => customerOptions.value.map(option => String(option.value)))

async function loadStats() {
	controller?.abort()
	const code = customer.value
	if (!code) {
		stats.value = null
		statsFailure.value = null
		return
	}
	const own = new AbortController()
	controller = own
	statsLoading.value = true
	statsFailure.value = null
	try {
		const { data } = await Api.talonMemory.getStats(code, own.signal)
		if (controller !== own) return
		stats.value = data
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		stats.value = null
		statsFailure.value = memoryFailure(err)
	} finally {
		if (controller === own) statsLoading.value = false
	}
}

function refresh() {
	loadStats()
	drawersList.value?.reload()
}

function applyFilter(kind: "room" | "source", value: string) {
	view.value = "drawers"
	if (kind === "room") room.value = value as TalonMemoryRoom
	else source.value = value as TalonMemorySource
}

function onForgotten(drawerId: string) {
	drawersList.value?.remove(drawerId)
	loadStats()
}

/** A customer the picker offers, or null. */
function offered(code: string | null | undefined): string | null {
	return code && codes.value.includes(code) ? code : null
}

// Seed from the global filter once the customers are known; with one customer, that one.
watch(
	codes,
	list => {
		if (customer.value) return
		customer.value = offered(globalCustomerCode.value) ?? (list.length === 1 ? list[0] : null)
	},
	{ immediate: true }
)
// The global filter wins when it changes. An emptied selection keeps the current customer: this view
// shows nothing without one.
onGlobalCustomerFilterChange(list => {
	const next = offered(list[0])
	if (next) customer.value = next
})
watch(customer, () => {
	room.value = null
	source.value = null
	openDrawer.value = null
	stats.value = null
	loadStats()
})

if (allowed.value) loadCustomers()
onBeforeUnmount(() => controller?.abort())
</script>
