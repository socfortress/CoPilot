<template>
	<div class="report-wizard">
		<n-spin v-model:show="loading">
			<n-form :label-width="80" class="flex flex-col gap-5">
				<div class="grid gap-5 grid-cols-1 sm:grid-cols-3">
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

					<n-form-item label="Time Range" v-if="canSelectPanels">
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
				</div>
				<div class="flex">
					<n-form-item label="Panels" v-if="canSelectPanels" class="grow">
						<n-select
							v-model:value="selectedPanels"
							:options="panelsOptions"
							:loading="loadingPanels"
							multiple
							clearable
						/>
					</n-form-item>
				</div>
				<div class="flex justify-end">
					<n-button type="success" @click="getLinks()" :loading="loadingLinks" v-if="isValid">
						<template #icon>
							<Icon :name="GenerateLinksIcon"></Icon>
						</template>
						Show Panels
					</n-button>
				</div>
			</n-form>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, watchEffect, watch } from "vue"
import { NSpin, NForm, NFormItem, NInputGroup, NInputNumber, NButton, NSelect, useMessage } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import type { Dashboard, Org, Panel, PanelLink } from "@/types/reporting"
import type { PanelsLinksPayload, PanelsLinksTimeUnit } from "@/api/reporting"
import { useStorage } from "@vueuse/core"

const emit = defineEmits<{
	(e: "reset"): void
	(e: "generated", value: PanelLink[]): void
}>()

const GenerateLinksIcon = "carbon:report-data"

const message = useMessage()
const orgsList = ref<Org[]>([])
const dashboardsList = ref<Dashboard[]>([])
const panelsList = ref<Panel[]>([])
const linksList = ref<PanelLink[]>([])
const loadingOrgs = ref(false)
const loadingDashboards = ref(false)
const loadingPanels = ref(false)
const loadingLinks = ref(false)
const selectedOrgId = ref<number | string | null>(null)
const selectedDashboardUID = ref<string | null>(null)
const selectedDashboard = computed(() =>
	selectedDashboardUID.value ? dashboardsList.value.find(o => o.uid === selectedDashboardUID.value) || null : null
)
const selectedPanels = ref<number[]>([])
const timeUnit = useStorage<PanelsLinksTimeUnit>("report-wizard-time-unit", "hours", localStorage)
const timeValue = useStorage<number>("report-wizard-time-value", 1, localStorage)

const loading = computed(
	() => loadingOrgs.value || loadingDashboards.value || loadingPanels.value || loadingLinks.value
)

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
const isValid = computed(() => canSelectPanels.value && selectedPanels.value.length)

watch([selectedOrgId, selectedDashboardUID, selectedPanels, timeUnit, timeValue], () => {
	emit("reset")
})

watch(selectedOrgId, val => {
	dashboardsList.value = []
	panelsList.value = []
	selectedDashboardUID.value = null
	selectedPanels.value = []

	if (val) {
		getDashboards()
	}
})

watch(selectedDashboardUID, val => {
	panelsList.value = []
	selectedPanels.value = []

	if (val) {
		getPanels()
	}
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

function getLinks() {
	if (
		selectedOrgId.value &&
		selectedDashboard.value &&
		selectedPanels.value.length &&
		timeUnit.value &&
		timeValue.value
	) {
		loadingLinks.value = true

		const payload: PanelsLinksPayload = {
			org_id: selectedOrgId.value,
			dashboard_title: selectedDashboard.value.title,
			dashboard_uid: selectedDashboard.value.uid,
			panel_ids: selectedPanels.value,
			time_range: {
				value: timeValue.value,
				unit: timeUnit.value
			}
		}

		Api.reporting
			.generatePanelsLinks(payload)
			.then(res => {
				if (res.data.success) {
					linksList.value = res.data?.links || []
					emit("generated", linksList.value)
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingLinks.value = false
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
