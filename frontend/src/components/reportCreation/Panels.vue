<template>
	<div class="report-panels">
		<div class="editor flex gap-3">
			<div class="panels-container grow">
				<div class="rows-container">
					<draggable
						v-model="rows"
						item-key="id"
						:animation="200"
						ghost-class="ghost-row"
						handle=".pan-area"
						group="rows"
						class="flex flex-col gap-2"
					>
						<template #item="{ element: row }">
							<div class="row">
								<draggable
									v-model="row.panels"
									item-key="id"
									:animation="200"
									ghost-class="ghost-panel"
									group="panels"
									class="flex gap-2"
								>
									<template #header>
										<div class="column-header flex justify-between">
											<Icon :name="PanIcon" :size="20" class="pan-area"></Icon>
										</div>
									</template>
									<template #item="{ element: panel }">
										<div class="panel">
											{{ panel.id }}
										</div>
									</template>
								</draggable>
							</div>
						</template>
						<template #footer>
							<div class="column flex items-center justify-center">
								<button class="add-task-btn flex items-center justify-center !mt-0" @click="addRow()">
									<Icon :name="AddIcon" :size="20"></Icon>
									<span>Add row</span>
								</button>
							</div>
						</template>
					</draggable>
				</div>
			</div>

			<div class="panels-sidebar flex flex-col gap-2 p-2">
				<draggable
					class="dragArea list-group"
					:list="availablePanels"
					:group="{ name: 'panels', pull: 'clone', put: false }"
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
		</div>

		<div class="toolbar mt-5">
			<n-button type="success" v-if="availablePanels?.length" @click="print()" :loading="loading">
				<template #icon>
					<Icon :name="PrintIcon"></Icon>
				</template>
				Print Report
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
/**
 * PDF:  ->  backend/report.pdf
 * TPL:  ->  backend/app/connectors/grafana/reporting/report-template-test.html
 */

import { ref, computed, toRefs, watch } from "vue"
import { NButton, NSlider, NPopover } from "naive-ui"
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
const PanIcon = "carbon:pan-horizontal"
const AddIcon = "carbon:add-alt"
const PrintIcon = "carbon:printer"
// const message = useMessage()
const loadingPrint = ref(false)
const loading = computed(() => loadingPrint.value)

const rows = ref<any[]>([])

function addRow() {
	rows.value.push({
		id: new Date().getTime(),
		panels: [{ id: new Date().getTime() + "a" }, { id: new Date().getTime() + "b" }]
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
	.editor {
		width: 100%;
		.panels-container {
			.rows-container {
				.row {
					border-radius: var(--border-radius);
					background-color: var(--bg-secondary-color);
					border: var(--border-small-050);
					display: flex;
					flex-wrap: wrap;
					padding: 20px;

					.panel {
						background-color: red;
						padding: 20px;
					}
				}
			}
		}

		.panels-sidebar {
			width: 180px;
			border-radius: var(--border-radius);
			background-color: var(--bg-secondary-color);
			border: var(--border-small-050);
			display: flex;
			flex-wrap: wrap;

			.panel {
				width: 100%;
				.content {
					border-radius: var(--border-radius);
					background-color: var(--bg-color);
					border: var(--border-small-050);
					overflow: hidden;
					display: flex;
					align-items: center;
					justify-content: center;
					aspect-ratio: 1.8;
					font-size: 12px;
					font-weight: bold;
					padding: 16px;
					text-align: center;
				}
			}
		}
	}
}
</style>
