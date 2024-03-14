<template>
	<div class="report-wizard">
		<n-spin v-model:show="loading">
			<n-form :label-width="80" class="flex flex-col gap-5">
				<div class="grid gap-5 grid-cols-1 sm:grid-cols-3">
					<n-form-item label="Time Range">
						<n-input-group>
							<n-select
								v-model:value="timeUnit"
								:options="timeUnitOptions"
								placeholder="Time unit"
								class="!min-w-28 basis-1"
							/>
							<n-input-number v-model:value="timeValue" :min="1" placeholder="Time" class="grow" />
						</n-input-group>
					</n-form-item>

					<n-form-item label="Organization">
						<n-select
							v-model:value="selectedOrgId"
							:options="orgsOptions"
							:loading="loadingOrgs"
							clearable
						/>
					</n-form-item>

					<n-form-item label="Dashboard" v-if="canSelectDashboard">
						<n-select
							v-model:value="selectedDashboardUID"
							:options="dashboardsOptions"
							:loading="loadingDashboards"
							clearable
						/>
					</n-form-item>
				</div>
				<div class="flex" v-if="!hidePanelsSelect">
					<n-form-item label="Panels" v-if="canSelectPanels" class="grow">
						<n-select
							v-model:value="selectedPanelsIds"
							:options="panelsOptions"
							:loading="loadingPanels"
							multiple
							clearable
						/>
					</n-form-item>
				</div>
			</n-form>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import { NSpin, NForm, NFormItem, NInputGroup, NInputNumber, NSelect, useMessage } from "naive-ui"
import Api from "@/api"
import type { Dashboard, Org, Panel } from "@/types/reporting"
import type { PanelsLinksTimeUnit } from "@/api/reporting"
import { useStorage } from "@vueuse/core"

const emit = defineEmits<{
	(e: "selected", value: Panel[]): void
	(e: "panels", value: Panel[]): void
	(e: "dashboard", value: Dashboard | null): void
	(e: "organization", value: Org | null): void
}>()

const props = defineProps<{
	hidePanelsSelect?: boolean
}>()
const { hidePanelsSelect } = toRefs(props)

const message = useMessage()
const orgsList = ref<Org[]>([])
const dashboardsList = ref<Dashboard[]>([])
const panelsList = ref<Panel[]>([])

const loadingOrgs = ref(false)
const loadingDashboards = ref(false)
const loadingPanels = ref(false)

const selectedOrgId = ref<number | string | null>(null)
const selectedOrg = computed(() =>
	selectedOrgId.value ? orgsList.value.find(o => o.id === selectedOrgId.value) || null : null
)
const selectedDashboardUID = ref<string | null>(null)
const selectedDashboard = computed(() =>
	selectedDashboardUID.value ? dashboardsList.value.find(o => o.uid === selectedDashboardUID.value) || null : null
)
const selectedPanelsIds = ref<number[]>([])
const selectedPanels = computed(() =>
	selectedPanelsIds.value ? panelsList.value.filter(o => selectedPanelsIds.value.includes(o.id)) : []
)
const timeUnit = useStorage<PanelsLinksTimeUnit>("report-wizard-time-unit", "hours", localStorage)
const timeValue = useStorage<number>("report-wizard-time-value", 1, localStorage)

const orgsOptions = computed(() => orgsList.value.map(o => ({ value: o.id, label: o.name })))
const dashboardsOptions = computed(() => dashboardsList.value.map(o => ({ value: o.uid, label: o.title })))
const panelsOptions = computed(() => panelsList.value.map(o => ({ value: o.id, label: o.title })))
const timeUnitOptions: { label: string; value: PanelsLinksTimeUnit }[] = [
	{ label: "Minutes", value: "minutes" },
	{ label: "Hours", value: "hours" },
	{ label: "Days", value: "days" }
]

const canSelectDashboard = computed(() => !!selectedOrgId.value)
const canSelectPanels = computed(() => canSelectDashboard.value && !!selectedDashboardUID.value)

const loading = computed(() => loadingOrgs.value || loadingDashboards.value || loadingPanels.value)

watch(selectedOrgId, val => {
	dashboardsList.value = []
	panelsList.value = []
	selectedDashboardUID.value = null
	selectedPanelsIds.value = []

	emit("organization", selectedOrg.value)

	if (val) {
		getDashboards()
	}
})

watch(selectedDashboardUID, val => {
	panelsList.value = []
	selectedPanelsIds.value = []

	emit("dashboard", selectedDashboard.value)

	if (val) {
		getPanels()
	}
})

watch(panelsList, val => {
	emit("panels", val)
})

watch(selectedPanelsIds, () => {
	emit("selected", selectedPanels.value)
})

function getOrgs() {
	loadingOrgs.value = true

	Api.reporting
		.getOrgs()
		.then(res => {
			if (res.data.success) {
				orgsList.value = res.data?.orgs || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingOrgs.value = false
		})
}

function getDashboards() {
	if (selectedOrgId.value) {
		loadingDashboards.value = true

		Api.reporting
			.getDashboards(selectedOrgId.value.toString())
			.then(res => {
				if (res.data.success) {
					dashboardsList.value = res.data?.dashboards || []
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingDashboards.value = false
			})
	}
}

function getPanels() {
	if (selectedDashboardUID.value) {
		loadingPanels.value = true

		Api.reporting
			.getPanels(selectedDashboardUID.value.toString())
			.then(res => {
				if (res.data.success) {
					panelsList.value = res.data?.panels || []
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingPanels.value = false
			})
	}
}

onBeforeMount(() => {
	getOrgs()
})
</script>

<style lang="scss" scoped>
.report-wizard {
	:deep() {
		.n-form-item-feedback-wrapper {
			display: none;
		}
	}
}
</style>
