<template>
	<div class="page page-min-wrapped kanban-app page-without-footer">
		<div class="scroll-wrap">
			<n-scrollbar x-scrollable>
				<div class="columns-scroll">
					<div class="columns-wrap flex">
						<draggable
							v-model="columns"
							item-key="title"
							:animation="200"
							ghost-class="ghost-column"
							handle=".pan-area"
							group="columns"
							class="flex items-start"
						>
							<template #item="{ element: column }">
								<div class="column">
									<draggable
										v-model="column.tasks"
										item-key="id"
										:animation="200"
										:handle="isMobile() ? '.pan-area' : undefined"
										ghost-class="ghost-card"
										group="tasks"
									>
										<template #header>
											<div class="column-header flex justify-between">
												<span @click="selectColumn(column)" class="flex items-center gap-3">
													<span>
														{{ column.title }}

														<Icon :name="EditIcon" :size="12"></Icon>
													</span>
													<span class="opacity-40">{{ column.tasks.length || 0 }}</span>
												</span>
												<Icon :name="PanIcon" :size="20" class="pan-area"></Icon>
											</div>
										</template>
										<template #item="{ element: task }">
											<TaskCard :task="task" :mobile="isMobile()" @click="selectTask(task)" />
										</template>
										<template #footer>
											<button
												class="add-task-btn flex items-center justify-center"
												@click="addTask(column)"
											>
												<Icon :name="AddIcon" :size="20"></Icon>
												<span>Add card</span>
											</button>
										</template>
									</draggable>
								</div>
							</template>
							<template #footer>
								<div class="column flex items-center justify-center">
									<button
										class="add-task-btn flex items-center justify-center !mt-0"
										@click="addColumn()"
									>
										<Icon :name="AddIcon" :size="20"></Icon>
										<span>Add column</span>
									</button>
								</div>
							</template>
						</draggable>
						<div class="spacer"></div>
					</div>
				</div>
			</n-scrollbar>
		</div>

		<n-modal v-model:show="showTaskEditor" class="kanban-modal">
			<div style="position: fixed; top: 20vw; left: 50vw; transform: translateX(-50%)">
				<TaskEditor :task="selectedTask" v-if="selectedTask" @close="selectedTask = null" />
			</div>
		</n-modal>

		<n-modal v-model:show="showColumnEditor" class="kanban-modal">
			<div style="position: fixed; top: 20vw; left: 50vw; transform: translateX(-50%)">
				<ColumnEditor :column="selectedColumn" v-if="selectedColumn" @close="selectedColumn = null" />
			</div>
		</n-modal>
	</div>
</template>

<script lang="ts" setup>
import { NScrollbar, NModal } from "naive-ui"
import draggable from "vuedraggable"
import TaskCard from "@/components/apps/Kanban/TaskCard.vue"
import TaskEditor from "@/components/apps/Kanban/TaskEditor.vue"
import ColumnEditor from "@/components/apps/Kanban/ColumnEditor.vue"
import { computed, ref } from "vue"
import { getTask, type Column, type Task } from "@/mock/kanban"
import dayjs from "@/utils/dayjs"
import { isMobile } from "@/utils"
import { useHideLayoutFooter } from "@/composables/useHideLayoutFooter"
import Icon from "@/components/common/Icon.vue"

const AddIcon = "carbon:add-alt"
const PanIcon = "carbon:pan-horizontal"
const EditIcon = "uil:edit-alt"

const selectedTask = ref<Task | null>(null)
const selectedColumn = ref<Column | null>(null)

const showTaskEditor = computed({ get: () => selectedTask.value !== null, set: () => (selectedTask.value = null) })
const showColumnEditor = computed({
	get: () => selectedColumn.value !== null,
	set: () => (selectedColumn.value = null)
})

const columns = ref(getTask())

function selectTask(task: Task) {
	selectedTask.value = task
}
function selectColumn(column: Column) {
	selectedColumn.value = column
}

function addColumn() {
	columns.value.push({
		id: new Date().getTime() + "",
		title: "Untitled",
		tasks: []
	})
}

function addTask(column: Column) {
	column.tasks.push({
		id: new Date().getTime() + "",
		title: "Untitled",
		date: dayjs().toDate(),
		dateText: dayjs().format("HH:mm")
	})
}

// :has() CSS relational pseudo-class not yet supported by Firefox
// (https://caniuse.com/css-has)
// at the moment this worker around permit to hide Layout Footer
useHideLayoutFooter()
</script>

<style lang="scss" scoped>
.page {
	:deep(.n-scrollbar-rail--horizontal) {
		left: var(--view-padding);
		right: var(--view-padding);
		overflow: hidden;
		border-radius: var(--n-scrollbar-border-radius);
	}

	.column {
		background-color: var(--bg-secondary-color);
		margin-left: 14px;
		width: 70vw;
		max-width: 320px;
		min-width: 300px;
		margin-top: 2px;
		margin-bottom: 20px;
		border-radius: var(--border-radius);
		border: 1px solid var(--border-color);
		padding: 10px;
		display: inline-block;
		transition: all 0.2s;

		&:first-child {
			margin-left: 0;
		}
		&:last-child {
			margin-right: var(--view-padding);
		}
		&:hover {
			border-color: var(--primary-color);
		}

		.column-header {
			margin-bottom: 10px;

			span {
				cursor: pointer;

				span:first-child {
					i {
						position: relative;
						top: 2px;
					}
				}

				&:hover {
					text-decoration-color: var(--primary-color);
					text-decoration-thickness: 2px;
				}
			}
		}

		.pan-area {
			cursor: ew-resize;
		}

		.add-task-btn {
			background-color: var(--primary-010-color);
			width: 100%;
			height: 50px;
			border-radius: var(--border-radius-small);
			font-size: 16px;
			color: var(--primary-color);
			margin-top: 10px;

			span {
				margin-left: 10px;
			}
		}
	}

	.spacer {
		width: calc(var(--view-padding) * 2);
	}

	.ghost-column,
	.ghost-card {
		box-shadow: 0px 0px 0px 2px var(--primary-color);
		opacity: 0.5;
	}
}
</style>
<style lang="scss">
#app {
	.layout {
		.main {
			// .view:has(.kanban-app) when will firefox have full compatibility
			.view {
				&.route-kanban,
				&.route-Apps-Kanban {
					padding-left: 0;
					padding-right: 0;

					.page {
						.columns-scroll {
							padding: 0 var(--view-padding);
						}
					}

					&.boxed {
						max-width: initial;

						.page {
							.columns-scroll {
								max-width: var(--boxed-width);
								margin: 0 auto;
								padding: 0;

								.columns-wrap {
									padding: 0 var(--view-padding);
								}
							}
						}
					}
				}
			}
		}
	}
}

.n-modal.kanban-modal {
	background-color: transparent;
}
</style>
