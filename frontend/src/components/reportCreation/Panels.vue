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
									<div class="row p-3">
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
				<div class="toolbar pr-4 flex items-center justify-between">
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

					<n-button type="success" @click="print()" :loading="loading" v-if="panelsReady">
						<template #icon>
							<Icon :name="PrintIcon"></Icon>
						</template>
						Print Report
					</n-button>
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
	</n-spin>
</template>

<script setup lang="ts">
/**
 * PDF:  ->  backend/report.pdf
 * TPL:  ->  backend/app/connectors/grafana/reporting/report-template-test.html
 */

// TODO: complete report.html

import { ref, computed, toRefs, watch } from "vue"
import { NButton, NSpin, NScrollbar, NTooltip, useMessage } from "naive-ui"
import type { Dashboard, Org, Panel } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import draggable from "vuedraggable"
import Api from "@/api"
import type { ReportTimeRange, RowPayload } from "@/api/reporting"
import { saveAs } from "file-saver"
import { useStorage } from "@vueuse/core"
import _kebabCase from "lodash/kebabCase"

// TODO: add logo input file and send in base64 . save on localstorage
// TODO: tenere in considerazione anche il "gap" della riga nel template
// TODO: aggiungere dentro il panel la dashboardTitle
// TODO: rimuovere "prepared by" dalla cover
// TODO: aggiunger drawer con form metadata (logo,company,theme, retina)

const ROW_WIDTH = 800
const ROW_HEIGHT = 320

interface OrgData {
	id: number
	rows: Row[]
}

interface Row {
	id: number
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
const AddIcon = "carbon:add-alt"
const PrintIcon = "carbon:printer"
const message = useMessage()
const loadingPrint = ref(false)
const loading = computed(() => loadingPrint.value)

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

function addRow() {
	rows.value.push({
		id: new Date().getTime(),
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

	const payload: RowPayload[] = []

	for (const row of rows.value) {
		if (row.panels.length) {
			const panel_width = (ROW_WIDTH / row.panels.length) * 2
			const panel_height = ROW_HEIGHT * 2

			payload.push({
				id: row.id,
				panels: row.panels.map(o => ({
					org_id: o.orgId,
					dashboard_title: o.dashboardTitle,
					dashboard_uid: o.dashboardUID,
					panel_id: o.panelId,
					panel_width,
					panel_height,
					// TODO: send real param
					theme: "light"
				}))
			})
		}
	}

	const reportFileName = `report${org.value?.name ? "-" + _kebabCase(org.value.name) : ""}.pdf`

	Api.reporting
		.generateReport(timerange.value, payload)
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
