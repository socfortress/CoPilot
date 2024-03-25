<template>
	<n-spin v-model:show="loading" class="overflow-hidden h-full w-full" content-class="overflow-hidden h-full w-full">
		<div class="report-panels h-full w-full flex gap-2" v-if="org">
			<div class="panels-container grow h-full flex flex-col gap-4">
				<div class="rows-container">
					<n-scrollbar style="max-height: 100%" trigger="none">
						<div class="drag-wrapper">
							<draggable
								v-model="rows"
								item-key="id"
								:animation="200"
								ghost-class="ghost-row"
								handle=".pan-area"
								:group="{ name: 'rows', pull: false, put: false }"
								class="flex flex-col gap-2"
							>
								<template #item="{ element: row }">
									<div class="row p-3" :class="{ 'height-large': row.height === 2 }">
										<div class="empty-message" v-if="!row.panels.length">Drop panels here</div>
										<draggable
											v-model="row.panels"
											item-key="id"
											:animation="200"
											ghost-class="ghost-panel"
											:group="{
												name: 'panels',
												put(to: any) {
													return to.el.children.length < 4
												},
												pull: ['panels']
											}"
											class="drop-panels-area flex gap-3 w-full h-full"
										>
											<template #header>
												<div class="left-box flex justify-end">
													<div class="pan-area">
														<Icon :name="PanIcon" :size="20"></Icon>
													</div>
													<div class="delete-box">
														<n-tooltip trigger="hover">
															<template #trigger>
																<n-button text @click="removeRow(row)" type="error">
																	<template #icon>
																		<Icon :name="CloseIcon"></Icon>
																	</template>
																</n-button>
															</template>
															Remove Row
														</n-tooltip>
													</div>
													<div class="settings-box">
														<n-popover trigger="click">
															<template #trigger>
																<n-button text>
																	<template #icon>
																		<Icon :name="RowSettingsIcon" :size="13"></Icon>
																	</template>
																</n-button>
															</template>

															<div class="py-1 flex gap-3 items-center">
																<div class="text-secondary-color text-sm">
																	Row height:
																</div>
																<n-switch
																	size="small"
																	v-model:value="row.height"
																	:unchecked-value="1"
																	:checked-value="2"
																>
																	<template #checked>
																		<small>Large</small>
																	</template>
																	<template #unchecked>
																		<small>Regular</small>
																	</template>
																</n-switch>
															</div>
														</n-popover>
													</div>
												</div>
											</template>
											<template #item="{ element: panel }">
												<div class="panel">
													<div class="delete-box">
														<n-tooltip trigger="hover">
															<template #trigger>
																<n-button
																	text
																	@click="removePanel(row, panel)"
																	type="error"
																>
																	<template #icon>
																		<Icon :name="CloseIcon"></Icon>
																	</template>
																</n-button>
															</template>
															Remove Panel
														</n-tooltip>
													</div>
													<div class="dashboard-title">
														{{ panel.dashboardTitle }}
													</div>
													<div class="content">
														{{ panel.panelTitle }}
													</div>
												</div>
											</template>
										</draggable>
									</div>
								</template>
							</draggable>
						</div>
					</n-scrollbar>
				</div>
				<div class="toolbar pr-4 flex items-center justify-between gap-2">
					<n-button
						class="add-task-btn flex items-center justify-center !mt-0"
						@click="addRow()"
						v-if="dashboard || panelsReady"
					>
						<template #icon>
							<Icon :name="AddIcon"></Icon>
						</template>
						<span>Add row</span>
					</n-button>

					<div class="flex items-center gap-2" v-if="panelsReady">
						<n-button type="success" @click="print()" :loading="loading">
							<template #icon>
								<Icon :name="PrintIcon"></Icon>
							</template>
							Print Report
						</n-button>
						<n-button type="success" @click="openSettings()" :loading="loading">
							<template #icon>
								<Icon :name="SettingsIcon"></Icon>
							</template>
						</n-button>
					</div>
				</div>
			</div>

			<div class="panels-sidebar h-full">
				<n-scrollbar style="max-height: 100%" trigger="none" v-if="dashboard && panelsList.length">
					<div class="p-3">
						<draggable
							class="flex flex-col gap-3"
							:list="panelsList"
							:group="{ name: 'panels', pull: 'clone', put: false }"
							:sort="false"
							item-key="id"
						>
							<template #item="{ element: panel }">
								<div class="panel">
									<div class="content">
										{{ panel.panelTitle }}
									</div>
								</div>
							</template>
						</draggable>
					</div>
				</n-scrollbar>
				<div v-else class="p-3 h-full">
					<div class="empty-message p-3">
						<div v-if="!dashboard">
							Select a
							<code>Dashboard</code>
							to get the panels
						</div>
						<div v-else>No Panels found</div>
					</div>
				</div>
			</div>
		</div>

		<div v-else class="empty-message">
			Select an
			<code>Organization</code>
			/
			<code>Dashboard</code>
			to create the Report
		</div>

		<n-drawer
			v-model:show="settingDrawerOpen"
			:width="500"
			style="max-width: 90vw"
			:trap-focus="false"
			:class="{ 'opacity-0': preloadingPrintSettings }"
			display-directive="show"
		>
			<n-drawer-content title="Report Settings" closable :native-scrollbar="false">
				<PrintSettings @update="printSettings = $event" />
			</n-drawer-content>
		</n-drawer>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, computed, toRefs, watch, onMounted } from "vue"
import { NButton, NSpin, NScrollbar, NTooltip, NDrawer, NDrawerContent, NPopover, NSwitch, useMessage } from "naive-ui"
import type { Dashboard, Org, Panel } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import PrintSettings, { type PrintSettingsData } from "./PrintSettings.vue"
import draggable from "vuedraggable"
import Api from "@/api"
import type { GenerateReportPayload, ReportTimeRange } from "@/api/reporting"
import { saveAs } from "file-saver"
import { useStorage } from "@vueuse/core"
import _kebabCase from "lodash/kebabCase"
import * as defaultSettings from "./defaultSettings"

const ROW_GAP = 20
const ROW_WIDTH = 800
const ROW_HEIGHT = 320

interface OrgData {
	id: number
	rows: Row[]
}

interface Row {
	id: number
	height: 1 | 2
	panels: PanelData[]
}

interface PanelData {
	panelId: number
	panelTitle: string
	orgId: number
	orgName: string
	dashboardUID: string
	dashboardTitle: string
}

const props = defineProps<{
	timerange: ReportTimeRange | null
	org: Org | null
	dashboard: Dashboard | null
	panels: Panel[]
}>()
const { timerange, org, dashboard, panels } = toRefs(props)

const PanIcon = "carbon:draggable"
const CloseIcon = "carbon:close"
const SettingsIcon = "carbon:settings"
const AddIcon = "carbon:add-alt"
const PrintIcon = "carbon:printer"
const RowSettingsIcon = "carbon:fit-to-height"
const message = useMessage()
const loadingPrint = ref(false)
const loading = computed(() => loadingPrint.value)

const settingDrawerOpen = ref(false)
const printSettings = ref<Partial<PrintSettingsData>>({})
const preloadingPrintSettings = ref(true)

const orgs = useStorage<OrgData[]>("report-panel-orgs-data", [], localStorage)
const rows = computed<Row[]>({
	get() {
		return orgs.value.find(o => o.id === org.value?.id)?.rows || []
	},
	set(val: Row[]) {
		const orgData = orgs.value.find(o => o.id === org.value?.id)
		if (orgData?.rows) {
			orgData.rows = val
		}
	}
})
const panelsList = ref<PanelData[]>([])

const panelsReady = computed<number>(() => {
	return rows.value.reduce((acc, row) => {
		return acc + row.panels.length
	}, 0)
})

watch(org, val => {
	if (val) {
		setOrg(val)
	}
	panelsList.value = []
})

watch(panels, val => {
	if (val?.length) {
		setPanelsList(val)

		if (!rows.value.length) {
			addRow()
		}
	}
})

function openSettings() {
	settingDrawerOpen.value = true
}

function addRow() {
	rows.value.push({
		id: new Date().getTime(),
		height: 1,
		panels: []
	})
}

function removeRow(row: Row) {
	rows.value.splice(
		rows.value.findIndex(o => o.id === row.id),
		1
	)
}
function removePanel(row: Row, panel: PanelData) {
	row.panels.splice(
		row.panels.findIndex(o => o.panelId === panel.panelId),
		1
	)
}

function setPanelsList(panels: Panel[]) {
	if (org.value && dashboard.value && panels.length) {
		panelsList.value = []

		for (const panel of panels) {
			panelsList.value.push({
				panelId: panel.id,
				panelTitle: panel.title,
				orgId: org.value.id,
				orgName: org.value.name,
				dashboardUID: dashboard.value.uid,
				dashboardTitle: dashboard.value.title
			})
		}
	}
}

function setOrg(org: Org) {
	const exist = orgs.value.find(o => o.id === org.id)
	if (!exist) {
		orgs.value.push({
			id: org.id,
			rows: []
		})
	}
}

function print() {
	if (!timerange.value) {
		return
	}

	loadingPrint.value = true

	const timeValue = parseInt(timerange.value.match(/\d+/)?.[0] || "1")
	const timeUnit = (timerange.value.match(/[a-z]/i)?.[0] || "h").toLocaleLowerCase()
	const timerangeText = `Last ${timeValue} ${timeUnit === "d" ? "Day" : timeUnit === "h" ? "Hour" : "minute"}${
		timeValue > 1 ? "s" : ""
	}`

	const payload: GenerateReportPayload = {
		timerange: timerange.value,
		timerange_text: timerangeText,
		logo_base64: printSettings.value.logo || defaultSettings.logo,
		company_name: printSettings.value.company || defaultSettings.company,
		rows: []
	}

	const density = printSettings.value.retina ? 2 : 1

	for (const row of rows.value) {
		if (row.panels.length) {
			const panel_width = ((ROW_WIDTH - ROW_GAP * (row.panels.length - 1)) / row.panels.length) * density
			const panel_height = ROW_HEIGHT * density * (row.height || 1)

			payload.rows.push({
				id: row.id,
				panels: row.panels.map(o => ({
					org_id: o.orgId,
					dashboard_title: o.dashboardTitle,
					dashboard_uid: o.dashboardUID,
					panel_id: o.panelId,
					panel_width,
					panel_height,
					theme: printSettings.value.theme || defaultSettings.theme
				}))
			})
		}
	}

	const reportFileName = `report${org.value?.name ? "-" + _kebabCase(org.value.name) : ""}.pdf`

	Api.reporting
		.generateReport(payload)
		.then(res => {
			if (res.data.success) {
				const dataUri = "data:application/pdf;base64," + res.data.base64_result
				saveAs(dataUri, reportFileName)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingPrint.value = false
		})
}

onMounted(() => {
	// need to preload print settings from drawer
	settingDrawerOpen.value = true
	setTimeout(() => {
		settingDrawerOpen.value = false
		setTimeout(() => {
			preloadingPrintSettings.value = false
		}, 300)
	}, 100)
})
</script>

<style lang="scss" scoped>
.empty-message {
	border: 2px dashed var(--border-color) !important;
	border-radius: var(--border-radius);
	height: 100%;
	width: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	text-align: center;
}
.report-panels {
	overflow: hidden;

	.panel {
		aspect-ratio: 1.72;
		cursor: move;

		.content {
			border-radius: var(--border-radius);
			background-color: var(--bg-color);
			border: var(--border-small-050);
			overflow: hidden;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 12px;
			font-weight: bold;
			padding: 16px;
			text-align: center;
			transition: border-color 0.2s;
			width: 100%;
			height: 100%;
		}

		&:hover {
			.content {
				border-color: var(--primary-040-color);
			}
		}

		&.ghost-panel {
			.content {
				border: 2px dashed var(--primary-040-color) !important;
			}
		}
	}

	.panels-container {
		overflow: hidden;

		.rows-container {
			overflow: hidden;
			border-radius: var(--border-radius);

			.drag-wrapper {
				padding-right: 16px;
				padding-left: 20px;
			}

			.row {
				border-radius: var(--border-radius);
				background-color: var(--bg-secondary-color);
				border: var(--border-small-050);
				height: 155px;
				position: relative;
				transition: border-color 0.2s;

				&.height-large {
					height: 300px;
				}
				.empty-message {
					position: absolute;
					z-index: 0;
					width: unset;
					height: unset;
					@apply top-3 bottom-3 left-3 right-3;
				}

				.drop-panels-area {
					position: absolute;
					width: unset;
					height: unset;
					@apply top-3 bottom-3 left-3 right-3;
				}

				.left-box {
					position: absolute;
					top: 0;
					left: -32px;
					bottom: 0;
					width: 25px;
					border: var(--border-small-050);
					background-color: var(--bg-secondary-color);
					border-radius: var(--border-radius);

					.pan-area {
						position: absolute;
						top: 50%;
						left: 2px;
						transform: translateY(-50%);
						cursor: move;
					}

					.delete-box {
						position: absolute;
						top: 0px;
						left: 0px;
						right: 0;
						background-color: rgba(var(--secondary4-color-rgb), 0.1);
						border-top-left-radius: var(--border-radius);
						border-top-right-radius: var(--border-radius);
						text-align: center;
						padding-top: 4px;
					}

					.settings-box {
						position: absolute;
						bottom: 0px;
						left: 0px;
						right: 0;
						background-color: var(--hover-005-color);
						border-bottom-left-radius: var(--border-radius);
						border-bottom-right-radius: var(--border-radius);
						text-align: center;
						padding-top: 4px;
					}

					&:hover {
						border-color: var(--primary-020-color);
					}
				}

				.panel {
					height: 100%;
					aspect-ratio: unset;
					flex: 1 1 0px;
					position: relative;

					.delete-box {
						position: absolute;
						top: 4px;
						right: 4px;
					}

					.dashboard-title {
						font-size: 10px;
						position: absolute;
						top: 0px;
						left: 0px;
						right: 28px;
						padding: 5px 10px;
						color: var(--fg-secondary-color);
						white-space: nowrap;
						overflow: hidden;
						text-overflow: ellipsis;
					}
				}

				&:hover {
					border-color: var(--primary-020-color);
				}

				&.ghost-row {
					border: 2px dashed var(--primary-040-color) !important;
				}
			}
		}
	}

	.panels-sidebar {
		border-radius: var(--border-radius);
		background-color: var(--bg-secondary-color);
		border: var(--border-small-050);
		width: 200px;

		:deep() {
			.n-scrollbar {
				.n-scrollbar-rail {
					right: 3px;
				}
			}
		}

		.panel {
			width: 100%;
		}
	}
}
</style>
