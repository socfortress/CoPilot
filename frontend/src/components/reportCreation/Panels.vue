<template>
	<n-spin v-model:show="loading" class="overflow-hidden h-full w-full" content-class="overflow-hidden h-full w-full">
		<div class="report-panels h-full w-full flex gap-2">
			<div class="panels-container grow h-full flex flex-col gap-4">
				<div class="rows-container" v-if="availablePanels?.length">
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
											class="flex gap-3 w-full h-full"
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
														{{ panel.title }}
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
				<div class="toolbar pr-4 flex items-center justify-between" v-if="availablePanels?.length">
					<n-button class="add-task-btn flex items-center justify-center !mt-0" @click="addRow()">
						<template #icon>
							<Icon :name="AddIcon"></Icon>
						</template>
						<span>Add row</span>
					</n-button>

					<n-button type="success" @click="print()" :loading="loading">
						<template #icon>
							<Icon :name="PrintIcon"></Icon>
						</template>
						Print Report
					</n-button>
				</div>
			</div>

			<div class="panels-sidebar h-full" v-if="availablePanels?.length">
				<n-scrollbar style="max-height: 100%" trigger="none">
					<div class="p-3">
						<draggable
							class="flex flex-col gap-3"
							:list="availablePanels"
							:group="{ name: 'panels', pull: 'clone', put: false }"
							:sort="false"
							item-key="id"
						>
							<template #item="{ element: panel }">
								<div class="panel">
									<div class="content">
										{{ panel.title }}
									</div>
								</div>
							</template>
						</draggable>
					</div>
				</n-scrollbar>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
/**
 * PDF:  ->  backend/report.pdf
 * TPL:  ->  backend/app/connectors/grafana/reporting/report-template-test.html
 */

import { ref, computed, toRefs, watch } from "vue"
import { NButton, NSlider, NSpin, NScrollbar, NTooltip } from "naive-ui"
import type { PanelLink, Panel } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import draggable from "vuedraggable"
// import Api from "@/api"
// import { saveAs } from "file-saver"

interface Row {
	id: number
	panels: Panel[]
}

const props = defineProps<{
	panelsList?: Panel[]
	availablePanels?: Panel[]
	linksList?: PanelLink[]
}>()
const { availablePanels } = toRefs(props)

// const MenuIcon = "carbon:overflow-menu-horizontal"
const PanIcon = "carbon:draggable"
const CloseIcon = "carbon:close"
const AddIcon = "carbon:add-alt"
const TrashIcon = "carbon:trash-can"
const PrintIcon = "carbon:printer"
// const message = useMessage()
const loadingPrint = ref(false)
const loading = computed(() => loadingPrint.value)
const rows = ref<Row[]>([])

watch(availablePanels, val => {
	if (val?.length && !rows.value.length) {
		addRow()
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
function removePanel(row: Row, panel: Panel) {
	row.panels.splice(
		row.panels.findIndex(o => o.id === panel.id),
		1
	)
}

function print() {
	loadingPrint.value = true

	setTimeout(() => {
		loadingPrint.value = false
	}, 2000)
}
</script>

<style lang="scss" scoped>
.report-panels {
	overflow: hidden;
	.panels-container {
		overflow: hidden;

		.rows-container {
			overflow: hidden;
			border-radius: var(--border-radius);

			.drag-wrapper {
				padding-right: 16px;
				padding-left: 30px;
			}

			.row {
				border-radius: var(--border-radius);
				background-color: var(--bg-secondary-color);
				border: var(--border-small-050);
				height: 155px;
				position: relative;
				transition: border-color 0.2s;

				.left-box {
					position: absolute;
					top: -1px;
					left: -30px;
					bottom: -1px;
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
						top: 3px;
						left: 3px;
					}
				}

				.panel {
					height: 130px;
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

		:deep() {
			.n-scrollbar {
				.n-scrollbar-rail {
					right: 3px;
				}
			}
		}
	}

	.panel {
		height: 100px;
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
}
</style>
