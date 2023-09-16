<template>
	<n-card class="task-editor">
		<div class="flex flex-col gap-2">
			<n-input
				v-model:value="task.title"
				placeholder="Task title..."
				type="textarea"
				size="large"
				:autosize="{
					minRows: 2,
					maxRows: 7
				}"
			/>
			<div class="flex justify-between">
				<div class="grow">
					<span
						class="task-label custom-label"
						v-if="task.label"
						:style="`--label-color:${labelsColors[task.label.id]}`"
					>
						{{ task.label.title }}
					</span>
				</div>
				<div class="flex items-center gap-4">
					<n-button v-if="task.id">Delete</n-button>
					<n-button @click="emit('close')" type="primary">Close</n-button>
				</div>
			</div>
		</div>
	</n-card>
</template>
<script lang="ts" setup>
import { NInput, NButton, NCard } from "naive-ui"
import { type Task } from "@/mock/kanban"
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

defineOptions({
	name: "TaskEditor"
})

const task = defineModel<Task>("task", { default: { title: "" } })

const emit = defineEmits<{
	(e: "close"): void
}>()

const secondaryColors = computed(() => useThemeStore().secondaryColors)

const labelsColors = {
	design: secondaryColors.value["secondary1"],
	"feature-request": secondaryColors.value["secondary2"],
	backend: secondaryColors.value["secondary3"],
	qa: secondaryColors.value["secondary4"]
} as unknown as { [key: string]: string }
</script>

<style lang="scss" scoped>
.task-editor {
	max-width: 500px;
	width: 80vw;

	.n-button {
		margin-top: 10px;
	}

	.custom-label::before {
		z-index: 0;
	}
}
</style>
