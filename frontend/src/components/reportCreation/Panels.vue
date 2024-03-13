<template>
	<div class="report-panels h-full w-full flex gap-3">
		<div class="panels-container grow h-full flex flex-col gap-4">
			<div class="rows-container grow" v-if="availablePanels?.length">
				<n-scrollbar style="max-height: 100%" trigger="none">
					<div class="pr-4">
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
								<div class="row">
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
										class="flex gap-2 w-full"
									>
										<template #header>
											<div class="row-header flex justify-end">
												<div class="pan-area">
													<Icon :name="PanIcon" :size="20"></Icon>
												</div>
											</div>
										</template>
										<template #item="{ element: panel }">
											<div class="panel">
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
					<Icon :name="AddIcon" :size="20"></Icon>
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
</template>

<script setup lang="ts">
/**
 * PDF:  ->  backend/report.pdf
 * TPL:  ->  backend/app/connectors/grafana/reporting/report-template-test.html
 */

import { ref, computed, toRefs, watch } from "vue"
import { NButton, NSlider, NPopover, NScrollbar } from "naive-ui"
import type { PanelLink, Panel } from "@/types/reporting"
import Icon from "@/components/common/Icon.vue"
import draggable from "vuedraggable"
// import Api from "@/api"
// import { saveAs } from "file-saver"

const props = defineProps<{
	panelsList?: Panel[]
	availablePanels?: Panel[]
	linksList?: PanelLink[]
}>()
const { availablePanels } = toRefs(props)

// const MenuIcon = "carbon:overflow-menu-horizontal"
const PanIcon = "carbon:draggable"
const AddIcon = "carbon:add-alt"
const PrintIcon = "carbon:printer"
// const message = useMessage()
const loadingPrint = ref(false)
const loading = computed(() => loadingPrint.value)

const rows = ref<{ id: number; panels: Panel[] }[]>([])

function addRow() {
	rows.value.push({
		id: new Date().getTime(),
		panels: []
	})
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

			.row {
				border-radius: var(--border-radius);
				background-color: var(--bg-secondary-color);
				border: var(--border-small-050);
				padding: 20px;
				height: 172px;
				position: relative;
				transition: border-color 0.2s;

				.row-header {
					position: absolute;
					top: 0;
					right: 0;
					bottom: 0;

					.pan-area {
						position: absolute;
						top: 50%;
						transform: translateY(-50%);
						cursor: move;
					}
				}

				.panel {
					height: 130px;
					aspect-ratio: unset;
					flex: 1 1 0px;
				}

				&:hover {
					border-color: var(--primary-color);
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
				border-color: var(--primary-color);
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
